"""Concrete Ebbinghaus to Semantic Graph projection bridge."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable

from hermes_constants import get_hermes_home
from plugins.semantic_graph.embedding import EmbeddingModelIdentity
from plugins.semantic_graph.sanitize import normalize_text, sanitize_text
from plugins.semantic_graph.store import SemanticGraphStore

from .policies import EbbinghausPolicies, is_protected
from .store import EbbinghausMemoryStore, _dream_idempotency_key, _timestamp_value

logger = logging.getLogger(__name__)

_PENDING_EVENT = "semantic_graph_bridge_pending"
_REPAIRED_EVENT = "semantic_graph_bridge_repaired"
_MAX_EVENT_SCAN = 5000


def bridge_is_enabled() -> bool:
    """Read the single operator-owned bridge switch without writing config."""
    from plugins.semantic_graph.config import load_config

    return load_config().cognitive_memory.bridge_enabled


def project_retention(
    cache: dict[str, Any] | None,
    *,
    now: float | None = None,
    expected_belief_version: int | None = None,
) -> float | None:
    """Project a valid cache row without mutating either canonical store."""
    if not cache:
        return None
    try:
        belief_version = int(cache["belief_version"])
        retention = float(cache["retention_at_sync"])
        stability_days = float(cache["stability_days"])
        source_updated_at = float(cache["source_updated_at"])
        synced_at = float(cache["synced_at"])
        current = float(time.time() if now is None else now)
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    values = (
        retention,
        stability_days,
        source_updated_at,
        synced_at,
        current,
    )
    if not all(math.isfinite(value) for value in values):
        return None
    if expected_belief_version is not None and belief_version != int(
        expected_belief_version
    ):
        return None
    if not 0.0 <= retention <= 1.0 or stability_days <= 0.0:
        return None
    if source_updated_at > synced_at or current < synced_at:
        return None
    elapsed_days = (current - synced_at) / 86_400.0
    projected = retention * math.exp(-(elapsed_days / stability_days))
    return max(0.0, min(1.0, projected))


def _failed_ids_hash(values: list[int]) -> str | None:
    if not values:
        return None
    rendered = "\n".join(str(value) for value in sorted(set(values)))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _stable_id(kind: str, *parts: object) -> str:
    raw = ":".join([kind, *(str(part) for part in parts)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _metadata_graph_id(node_id: str) -> str:
    """Keep a structural hash recoverable without resembling an opaque secret."""
    return ":".join(node_id[index : index + 16] for index in range(0, len(node_id), 16))


def _split_tags(raw: Any) -> list[str]:
    if isinstance(raw, str):
        values = raw.replace(";", ",").split(",")
    elif isinstance(raw, (list, tuple, set, frozenset)):
        values = [str(value) for value in raw]
    else:
        values = []
    return sorted({value.strip().lower() for value in values if value.strip()})


def _node_shape(memory: dict[str, Any]) -> tuple[str, str]:
    tags = set(_split_tags(memory.get("tags")))
    source = str(memory.get("source") or "").strip().lower()
    memory_type = str(memory.get("memory_type") or "").strip().lower()
    # Tags-based classification (higher priority than memory_type)
    if source == "validated_insight" or {"insight", "validated"} <= tags:
        return "Claim", "memory.insight"
    if "preference" in tags:
        return "Preference", "memory.preference"
    if "goal" in tags:
        return "Goal", "memory.goal"
    if "decision" in tags:
        return "Decision", "memory.decision"
    if "procedure" in tags or "skill" in tags:
        return "Procedure", "memory.procedure"
    if "policy" in tags or "policy-fact" in tags:
        return "Claim", "memory.policy"
    if "concept" in tags:
        return "Concept", "memory.concept"
    # Memory-type fallback
    if memory_type == "episodic":
        return "Event", "memory.episodic"
    if memory_type == "semantic":
        return "Claim", "memory.semantic"
    if memory_type == "procedural":
        return "Procedure", "memory.procedural"
    return "Claim", "memory.fact"


def _graph_status(belief_status: str) -> str:
    status = str(belief_status or "current").strip().lower()
    if status == "superseded":
        return "superseded"
    if status == "retracted":
        return "rejected"
    if status in {"contested", "unverified"}:
        return "candidate"
    return "asserted"


class EbbinghausSemanticGraphBridge:
    """Eventually-consistent projection over the two existing SQLite stores."""

    def __init__(
        self,
        graph_store: SemanticGraphStore,
        *,
        memory_store: EbbinghausMemoryStore | None = None,
    ) -> None:
        self._graph_store = graph_store
        self._memory_store = memory_store
        if memory_store is not None:
            self._memory_db_path = Path(memory_store.db_path)
            self._memory_policies = memory_store.policies
        else:
            self._memory_db_path, self._memory_policies = (
                self._resolve_operator_memory_config()
            )

    @staticmethod
    def _resolve_operator_memory_config() -> tuple[Path, EbbinghausPolicies]:
        from . import _load_plugin_config

        raw = _load_plugin_config()
        policies = EbbinghausPolicies.from_plugin_config(raw)
        hermes_home = get_hermes_home()
        configured = str(raw.get("db_path") or hermes_home / "ebbinghaus_memory.db")
        configured = configured.replace("$HERMES_HOME", str(hermes_home))
        configured = configured.replace("${HERMES_HOME}", str(hermes_home))
        return Path(configured).expanduser(), policies

    def _read_connection(self) -> sqlite3.Connection:
        uri = self._memory_db_path.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _memory_ids(self, limit: int) -> list[int]:
        if not self._memory_db_path.exists():
            return []
        with self._read_connection() as conn:
            rows = conn.execute(
                "SELECT memory_id FROM memories "
                "ORDER BY updated_at DESC, memory_id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [int(row["memory_id"]) for row in rows]

    def _raw_memory(self, memory_id: int) -> dict[str, Any]:
        with self._read_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE memory_id = ?",
                (int(memory_id),),
            ).fetchone()
        if row is None:
            raise KeyError(f"memory_id not found: {memory_id}")
        return dict(row)

    def _dream_provenance(self, semantic_memory_id: int) -> list[dict[str, Any]]:
        with self._read_connection() as conn:
            rows = conn.execute(
                "SELECT source_memory_id, relation, created_at FROM memory_provenance "
                "WHERE semantic_memory_id = ? ORDER BY source_memory_id",
                (int(semantic_memory_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def _dream_sources(self, semantic_memory_id: int) -> list[int]:
        return [
            int(row["source_memory_id"])
            for row in self._dream_provenance(semantic_memory_id)
        ]

    @staticmethod
    def _embedding_namespace() -> str:
        """Resolve representation identity without probing or starting a server."""
        try:
            from plugins.semantic_graph.config import load_config

            config = load_config().embedding
            return EmbeddingModelIdentity(
                provider="llama.cpp",
                model=config.model,
                revision=config.revision,
                dimensions=config.dimensions,
                serializer_version=config.serializer_version,
            ).namespace
        except Exception:
            return "unavailable"

    def _open_apply_store(self) -> tuple[EbbinghausMemoryStore, bool]:
        if self._memory_store is not None:
            return self._memory_store, False
        return (
            EbbinghausMemoryStore(
                self._memory_db_path,
                policies=self._memory_policies,
            ),
            True,
        )

    @staticmethod
    def _belief_id(memory: dict[str, Any]) -> str:
        memory_id = int(memory["memory_id"])
        return str(memory.get("belief_id") or f"memory-{memory_id}")

    def _state_cache(
        self,
        memory_store: EbbinghausMemoryStore,
        memory: dict[str, Any],
        raw: dict[str, Any],
        *,
        synced_at: float,
    ) -> dict[str, Any]:
        tags = _split_tags(memory.get("tags"))
        return {
            "memory_id": int(memory["memory_id"]),
            "belief_id": str(raw.get("belief_id") or self._belief_id(memory)),
            "belief_version": int(raw.get("belief_version") or 1),
            "access_state": str(memory.get("access_state") or "accessible"),
            "belief_status": str(memory.get("belief_status") or "current"),
            "memory_state": str(memory.get("state") or "active"),
            "retention_at_sync": max(
                0.0,
                min(1.0, float(memory.get("retention") or 0.0)),
            ),
            "stability_days": max(
                0.05,
                float(memory.get("stability_days") or 0.05),
            ),
            "salience": max(0.0, min(1.0, float(memory.get("salience") or 0.0))),
            "valence": max(-1.0, min(1.0, float(memory.get("valence") or 0.0))),
            "confidence": max(
                0.0,
                min(1.0, float(memory.get("confidence") or 0.0)),
            ),
            "protected": is_protected(
                tags,
                memory_store.policies.capacity.protected_tags,
            ),
            "source_updated_at": _timestamp_value(raw.get("updated_at")),
            "synced_at": float(synced_at),
        }

    def _sync_memory(
        self,
        memory_store: EbbinghausMemoryStore,
        memory_id: int,
    ) -> str:
        memory = memory_store.get(int(memory_id))
        raw = self._raw_memory(int(memory_id))
        belief_id = str(raw.get("belief_id") or self._belief_id(memory))
        belief_version = int(raw.get("belief_version") or 1)
        identity_key = f"ebbinghaus:{belief_id}:v{belief_version}"
        node_id = _stable_id("ebbinghaus-node", identity_key)
        cleaned = sanitize_text(str(memory.get("content") or ""), max_chars=4000)
        label = cleaned.text[:500] or f"Ebbinghaus memory {int(memory_id)}"
        node_type, subtype = _node_shape(memory)
        tags = set(_split_tags(memory.get("tags")))
        with self._graph_store.transaction():
            self._graph_store.upsert_node(
                {
                    "node_id": node_id,
                    "node_type": node_type,
                    "subtype": subtype,
                    "label": label,
                    "normalized_label": normalize_text(label).casefold(),
                    "summary": cleaned.text,
                    "identity_key": identity_key,
                    "status": _graph_status(str(memory.get("belief_status") or "")),
                    "authority": "user" if "user" in tags else "assistant",
                    "confidence": max(
                        0.0,
                        min(1.0, float(memory.get("confidence") or 0.0)),
                    ),
                    "salience": max(
                        0.0,
                        min(1.0, float(memory.get("salience") or 0.0)),
                    ),
                    "metadata": {
                        "ebbinghaus_memory_id": int(memory_id),
                        "ebbinghaus_belief_id": belief_id,
                        "ebbinghaus_belief_version": belief_version,
                        "bridge_relation": "represents",
                        "redaction_count": cleaned.redaction_count,
                    },
                }
            )
            self._graph_store.upsert_memory_node_link(
                {
                    "memory_id": int(memory_id),
                    "node_id": node_id,
                    "belief_id": belief_id,
                    "belief_version": belief_version,
                    "relation": "represents",
                }
            )
            self._graph_store.upsert_memory_state_cache(
                self._state_cache(
                    memory_store,
                    memory,
                    raw,
                    synced_at=time.time(),
                )
            )
        return node_id

    def _sync_revision(
        self,
        memory_store: EbbinghausMemoryStore,
        old_memory_id: int,
        new_memory_id: int,
    ) -> None:
        with self._graph_store.transaction():
            old_node_id = self._sync_memory(memory_store, old_memory_id)
            new_node_id = self._sync_memory(memory_store, new_memory_id)
            current = memory_store.get(new_memory_id)
            self._graph_store.upsert_edge(
                {
                    "edge_id": _stable_id(
                        "ebbinghaus-edge",
                        new_node_id,
                        old_node_id,
                        "supersedes",
                    ),
                    "source_node_id": new_node_id,
                    "target_node_id": old_node_id,
                    "edge_type": "supersedes",
                    "relation_label": "belief_revision",
                    "strength": 1.0,
                    "confidence": max(
                        0.0,
                        min(1.0, float(current.get("confidence") or 0.0)),
                    ),
                    "status": "asserted",
                    "rationale": "Ebbinghaus belief revision",
                    "metadata": {},
                }
            )

    def _sync_dream(
        self,
        memory_store: EbbinghausMemoryStore,
        semantic_memory_id: int,
    ) -> dict[str, Any]:
        with self._graph_store.transaction():
            semantic_node_id = self._sync_memory(
                memory_store,
                semantic_memory_id,
            )
            semantic = memory_store.get(semantic_memory_id)
            provenance_rows = self._dream_provenance(semantic_memory_id)
            source_ids = [
                int(row["source_memory_id"]) for row in provenance_rows
            ]
            source_node_ids: list[str] = []
            for source_id in source_ids:
                source_node_id = self._sync_memory(memory_store, source_id)
                source_node_ids.append(source_node_id)
            applied_at = max(
                (float(row.get("created_at") or 0.0) for row in provenance_rows),
                default=float(time.time()),
            )
            metadata = {
                "source_memory_ids": source_ids,
                "source_graph_node_ids": source_node_ids,
                "provenance": [
                    {
                        "source_memory_id": source_id,
                        "source_graph_node_id": source_node_id,
                        "relation": str(row.get("relation") or "dream-derived"),
                    }
                    for source_id, source_node_id, row in zip(
                        source_ids,
                        source_node_ids,
                        provenance_rows,
                    )
                ],
                "applied_at": applied_at,
                "embedding_namespace": self._embedding_namespace(),
                "validation_state": "apply_validated",
                "idempotency_key": _dream_idempotency_key(source_ids),
            }
            persisted_metadata = {
                **metadata,
                "source_graph_node_ids": [
                    _metadata_graph_id(node_id) for node_id in source_node_ids
                ],
                "provenance": [
                    {
                        **item,
                        "source_graph_node_id": _metadata_graph_id(
                            str(item["source_graph_node_id"])
                        ),
                    }
                    for item in metadata["provenance"]
                ],
                "graph_node_id_encoding": "colon-separated-hex",
            }
            self._graph_store.upsert_node(
                {
                    "node_id": semantic_node_id,
                    "metadata": persisted_metadata,
                }
            )
            for source_id, source_node_id in zip(source_ids, source_node_ids):
                self._graph_store.upsert_edge(
                    {
                        "edge_id": _stable_id(
                            "ebbinghaus-edge",
                            semantic_node_id,
                            source_node_id,
                            "derived_from",
                        ),
                        "source_node_id": semantic_node_id,
                        "target_node_id": source_node_id,
                        "edge_type": "derived_from",
                        "relation_label": "dream",
                        "strength": 1.0,
                        "confidence": max(
                            0.0,
                            min(1.0, float(semantic.get("confidence") or 0.0)),
                        ),
                        "status": "asserted",
                        "rationale": "Ebbinghaus dream provenance",
                        "metadata": {
                            **persisted_metadata,
                            "edge_source_memory_id": source_id,
                            "edge_source_graph_node_id": _metadata_graph_id(
                                source_node_id
                            ),
                        },
                    }
                )
        return metadata

    @staticmethod
    def _error_hash(exc: Exception) -> str:
        rendered = f"{type(exc).__name__}:{exc}"
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def _record_pending(
        self,
        memory_store: EbbinghausMemoryStore,
        *,
        operation: str,
        memory_id: int,
        related_memory_id: int | None,
        exc: Exception,
    ) -> int | None:
        try:
            memory = memory_store.get(memory_id)
            return memory_store.experience.record_event(
                _PENDING_EVENT,
                memory_id=memory_id,
                related_memory_id=related_memory_id,
                belief_id=self._belief_id(memory),
                payload={
                    "operation": operation,
                    "error_hash": self._error_hash(exc),
                },
            )
        except Exception as ledger_exc:
            logger.warning(
                "Ebbinghaus semantic graph bridge and pending ledger failed: %s",
                self._error_hash(ledger_exc),
            )
            return None

    def _best_effort(
        self,
        *,
        operation: str,
        memory_id: int,
        related_memory_id: int | None,
        action: Callable[[], None],
    ) -> dict[str, Any]:
        if self._memory_store is None:
            raise RuntimeError("live bridge operation requires an Ebbinghaus store")
        try:
            action()
            return {"success": True, "operation": operation}
        except Exception as exc:
            event_id = self._record_pending(
                self._memory_store,
                operation=operation,
                memory_id=memory_id,
                related_memory_id=related_memory_id,
                exc=exc,
            )
            logger.warning(
                "Ebbinghaus semantic graph bridge deferred operation=%s error_hash=%s",
                operation,
                self._error_hash(exc),
            )
            return {
                "success": False,
                "operation": operation,
                "repair_pending": event_id is not None,
            }

    def after_remember(self, result: dict[str, Any]) -> dict[str, Any]:
        memory_id = result.get("memory_id")
        if memory_id is None:
            return {"success": True, "operation": "remember", "skipped": True}
        return self._best_effort(
            operation="remember",
            memory_id=int(memory_id),
            related_memory_id=None,
            action=lambda: self._sync_memory(self._memory_store, int(memory_id)),  # type: ignore[arg-type]
        )

    def after_revision(self, result: dict[str, Any]) -> dict[str, Any]:
        old_id = int(result["old_memory_id"])
        new_id = int(result["new_memory_id"])
        return self._best_effort(
            operation="revise",
            memory_id=new_id,
            related_memory_id=old_id,
            action=lambda: self._sync_revision(self._memory_store, old_id, new_id),  # type: ignore[arg-type]
        )

    def after_retraction(self, result: dict[str, Any]) -> dict[str, Any]:
        memory_id = int(result["memory_id"])
        return self._best_effort(
            operation="retract",
            memory_id=memory_id,
            related_memory_id=None,
            action=lambda: self._sync_memory(self._memory_store, memory_id),  # type: ignore[arg-type]
        )

    def after_dream_apply(self, result: dict[str, Any]) -> dict[str, Any]:
        outcomes: list[dict[str, Any]] = []
        for item in result.get("applied") or []:
            memory_id = int(item["semantic_memory_id"])
            graph_metadata: dict[str, Any] = {}

            def sync_dream(memory_id: int = memory_id) -> None:
                nonlocal graph_metadata
                graph_metadata = self._sync_dream(
                        self._memory_store,  # type: ignore[arg-type]
                        memory_id,
                )

            outcome = self._best_effort(
                operation="dream",
                memory_id=memory_id,
                related_memory_id=None,
                action=sync_dream,
            )
            if outcome["success"]:
                item.update(graph_metadata)
            outcomes.append(outcome)
        return {
            "success": all(item["success"] for item in outcomes),
            "operation": "dream",
            "processed": len(outcomes),
        }

    def sync(self, *, limit: int, dry_run: bool) -> dict[str, Any]:
        ids = self._memory_ids(limit)
        result: dict[str, Any] = {
            "success": True,
            "dry_run": bool(dry_run),
            "selected": len(ids),
            "would_sync": len(ids),
            "synced": 0,
            "failed": 0,
            "failed_memory_ids_hash": None,
        }
        if dry_run or not ids:
            return result
        memory_store, owned = self._open_apply_store()
        failed: list[int] = []
        try:
            for memory_id in ids:
                try:
                    self._sync_memory(memory_store, memory_id)
                    result["synced"] += 1
                except Exception as exc:
                    failed.append(memory_id)
                    self._record_pending(
                        memory_store,
                        operation="remember",
                        memory_id=memory_id,
                        related_memory_id=None,
                        exc=exc,
                    )
        finally:
            if owned:
                memory_store.close()
        result["failed"] = len(failed)
        result["failed_memory_ids_hash"] = _failed_ids_hash(failed)
        result["success"] = not failed
        return result

    def _pending_events(self, limit: int) -> list[dict[str, Any]]:
        if not self._memory_db_path.exists():
            return []
        with self._read_connection() as conn:
            rows = conn.execute(
                """
                SELECT event_id, event_type, memory_id, related_memory_id,
                       belief_id, payload, created_at
                FROM memory_events
                WHERE event_type IN (?, ?)
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (_PENDING_EVENT, _REPAIRED_EVENT, _MAX_EVENT_SCAN),
            ).fetchall()
        repaired: set[int] = set()
        pending: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row["payload"] or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            if row["event_type"] == _REPAIRED_EVENT:
                try:
                    repaired.add(int(payload["pending_event_id"]))
                except (KeyError, TypeError, ValueError):
                    pass
                continue
            pending.append(
                {
                    "event_id": int(row["event_id"]),
                    "memory_id": int(row["memory_id"]),
                    "related_memory_id": (
                        int(row["related_memory_id"])
                        if row["related_memory_id"] is not None
                        else None
                    ),
                    "belief_id": str(row["belief_id"] or ""),
                    "payload": payload if isinstance(payload, dict) else {},
                }
            )
        return [
            event
            for event in pending
            if event["event_id"] not in repaired
        ][: max(1, int(limit))]

    def _repair_event(
        self,
        memory_store: EbbinghausMemoryStore,
        event: dict[str, Any],
    ) -> None:
        operation = str(event["payload"].get("operation") or "")
        memory_id = int(event["memory_id"])
        related = event.get("related_memory_id")
        if operation == "remember":
            self._sync_memory(memory_store, memory_id)
        elif operation == "revise" and related is not None:
            self._sync_revision(memory_store, int(related), memory_id)
        elif operation == "retract":
            self._sync_memory(memory_store, memory_id)
        elif operation == "dream":
            self._sync_dream(memory_store, memory_id)
        else:
            raise ValueError("unsupported pending bridge operation")

    def repair(self, *, limit: int, dry_run: bool) -> dict[str, Any]:
        events = self._pending_events(limit)
        result: dict[str, Any] = {
            "success": True,
            "dry_run": bool(dry_run),
            "selected": len(events),
            "would_repair": len(events),
            "repaired": 0,
            "failed": 0,
            "failed_event_ids_hash": None,
        }
        if dry_run or not events:
            return result
        memory_store, owned = self._open_apply_store()
        failed: list[int] = []
        try:
            for event in events:
                try:
                    self._repair_event(memory_store, event)
                    memory_store.experience.record_event(
                        _REPAIRED_EVENT,
                        memory_id=event["memory_id"],
                        related_memory_id=event.get("related_memory_id"),
                        belief_id=event.get("belief_id", ""),
                        payload={
                            "pending_event_id": event["event_id"],
                            "operation": event["payload"].get("operation", ""),
                        },
                    )
                    result["repaired"] += 1
                except Exception:
                    failed.append(int(event["event_id"]))
        finally:
            if owned:
                memory_store.close()
        result["failed"] = len(failed)
        result["failed_event_ids_hash"] = _failed_ids_hash(failed)
        result["success"] = not failed
        return result

    def status(self) -> dict[str, Any]:
        graph = self._graph_store.get_status_counts()
        memory_count = len(self._memory_ids(_MAX_EVENT_SCAN))
        pending_count = len(self._pending_events(_MAX_EVENT_SCAN))
        valid_projection_count = sum(
            project_retention(row) is not None
            for row in self._graph_store.list_memory_state_cache(
                limit=_MAX_EVENT_SCAN
            )
        )
        return {
            "success": True,
            "memory_db_exists": self._memory_db_path.exists(),
            "memory_count": memory_count,
            "memory_node_links": graph["memory_node_links"],
            "memory_state_cache": graph["memory_state_cache"],
            "valid_projection_count": valid_projection_count,
            "repair_pending": pending_count,
        }
