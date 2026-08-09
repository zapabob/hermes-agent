"""Semantic Graph runtime — tools + lifecycle hooks."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, Optional

from . import graph as _graph
from .config import SemanticGraphConfig, load_config
from .exporter import ExportPathError, export_graph
from .inference import SemanticGraphInference, SemanticGraphInferenceError
from .retrieval import render_context, search_and_rank
from .sanitize import normalize_text, sanitize_metadata, sanitize_text
from .store import SemanticGraphStore, new_id

logger = logging.getLogger("hermes.plugins.semantic_graph")


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SemanticGraphRuntime:
    def __init__(self, llm: Any = None, config: Optional[SemanticGraphConfig] = None) -> None:
        self._llm = llm
        self._config = config or load_config()
        self._store: Optional[SemanticGraphStore] = None
        self._inference = SemanticGraphInference(llm=llm)
        self._turn_seen: set[str] = set()

    def check_available(self) -> bool:
        return True

    @property
    def config(self) -> SemanticGraphConfig:
        return self._config

    def store(self) -> SemanticGraphStore:
        if self._store is None:
            self._store = SemanticGraphStore(self._config.db_path())
            self._store.ensure_ready()
        return self._store

    # ------------------------------------------------------------------ tools

    def handle_status(self, args: Optional[dict] = None, **_kw: Any) -> str:
        try:
            counts = self.store().get_status_counts()
            return _json(
                {
                    "success": True,
                    "db_path": str(self._config.db_path()),
                    **counts,
                    "capture_turns": self._config.capture_turns,
                    "capture_tool_events": self._config.capture_tool_events,
                    "auto_extract": self._config.auto_extract,
                    "retrieval_enabled": self._config.retrieval_enabled,
                }
            )
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_begin_run(self, args: Optional[dict] = None, **kw: Any) -> str:
        args = args or {}
        objective = normalize_text(str(args.get("objective") or ""))
        if not objective:
            return _json({"success": False, "error": "objective required"})
        try:
            row = self.store().create_run(
                objective=objective,
                scope=str(args.get("scope") or "run"),
                title=str(args.get("title") or ""),
                session_id=str(kw.get("session_id") or ""),
                turn_id=str(kw.get("turn_id") or ""),
                model=str(kw.get("model") or ""),
                platform=str(kw.get("platform") or ""),
                metadata=sanitize_metadata(args.get("metadata") or {}),
            )
            return _json({"success": True, **row})
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_ingest(self, args: Optional[dict] = None, **kw: Any) -> str:
        args = args or {}
        text = str(args.get("text") or "")
        source_kind = str(args.get("source_kind") or "")
        if not text or not source_kind:
            return _json({"success": False, "error": "text and source_kind required"})
        cleaned = sanitize_text(text, max_chars=self._config.max_artifact_chars)
        authority = str(args.get("authority") or "external")
        try:
            art = self.store().upsert_artifact(
                {
                    "artifact_type": source_kind,
                    "title": str(args.get("title") or ""),
                    "content": cleaned.text,
                    "content_hash": _hash(cleaned.text),
                    "authority": authority,
                    "run_id": args.get("run_id"),
                    "session_id": str(kw.get("session_id") or ""),
                    "turn_id": str(kw.get("turn_id") or ""),
                    "model": str(kw.get("model") or ""),
                    "platform": str(kw.get("platform") or ""),
                    "truncated": cleaned.truncated,
                    "redaction_count": cleaned.redaction_count,
                    "metadata": sanitize_metadata(
                        {
                            **(args.get("metadata") or {}),
                            "subtype": args.get("subtype") or "",
                        }
                    ),
                }
            )
            out: dict[str, Any] = {"success": True, **art}
            if args.get("extract"):
                try:
                    fragment = self._inference.extract_fragment(
                        json.dumps(
                            {
                                "artifact_id": art["artifact_id"],
                                "content": cleaned.text,
                            },
                            ensure_ascii=False,
                        )
                    )
                    run_id = args.get("run_id")
                    if not run_id:
                        run = self.store().create_run(
                            objective="ingest extract",
                            session_id=str(kw.get("session_id") or ""),
                        )
                        run_id = run["run_id"]
                    applied = _graph.apply_fragment_to_store(
                        self.store(),
                        run_id,
                        fragment,
                        producer_role="extractor",
                        producer_type="plugin_llm",
                    )
                    out["extract"] = applied
                except SemanticGraphInferenceError as exc:
                    out["extract"] = {"success": False, "error": str(exc)}
            return _json(out)
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_submit_fragment(self, args: Optional[dict] = None, **_kw: Any) -> str:
        args = args or {}
        run_id = str(args.get("run_id") or "")
        fragment = args.get("fragment")
        producer_role = str(args.get("producer_role") or "")
        if not run_id or not isinstance(fragment, dict) or not producer_role:
            return _json(
                {
                    "success": False,
                    "error": "run_id, producer_role, and fragment object required",
                }
            )
        if self.store().get_run(run_id) is None:
            return _json({"success": False, "error": f"unknown run_id: {run_id}"})
        try:
            result = _graph.apply_fragment_to_store(
                self.store(),
                run_id,
                fragment,
                producer_role=producer_role,
                producer_id=str(args.get("producer_id") or ""),
                model=str(args.get("model") or ""),
                fragment_id=args.get("fragment_id"),
            )
            return _json(result)
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_search(self, args: Optional[dict] = None, **_kw: Any) -> str:
        args = args or {}
        query = str(args.get("query") or "")
        if not query:
            return _json({"success": False, "error": "query required"})
        top_k = int(args.get("top_k") or self._config.retrieval_top_k)
        top_k = max(1, min(20, top_k))
        statuses = args.get("statuses") or list(self._config.recall_statuses)
        try:
            hits = search_and_rank(
                self.store(),
                query,
                top_k=top_k,
                min_confidence=self._config.min_recall_confidence,
                statuses=list(statuses),
                node_types=args.get("node_types"),
                subtypes=args.get("subtypes"),
                authorities=args.get("authorities"),
                run_id=args.get("run_id"),
            )
            if args.get("include_artifacts"):
                for hit in hits:
                    hit["artifacts"] = self.store().list_artifacts(
                        run_id=args.get("run_id"), limit=20
                    )
            if args.get("include_evidence"):
                for hit in hits:
                    hit["evidence"] = self.store().list_evidence_for_node(hit["node_id"])
            return _json({"success": True, "results": hits, "count": len(hits)})
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_get(self, args: Optional[dict] = None, **_kw: Any) -> str:
        args = args or {}
        object_type = str(args.get("object_type") or "")
        object_id = str(args.get("object_id") or "")
        if not object_type or not object_id:
            return _json({"success": False, "error": "object_type and object_id required"})
        store = self.store()
        getters = {
            "run": store.get_run,
            "node": store.get_node,
            "edge": store.get_edge,
            "artifact": store.get_artifact,
            "fragment": store.get_fragment,
            "evaluation": store.get_evaluation,
        }
        getter = getters.get(object_type)
        if getter is None:
            return _json({"success": False, "error": f"unknown object_type: {object_type}"})
        try:
            obj = getter(object_id)
            if obj is None:
                return _json({"success": False, "error": "not found"})
            out: dict[str, Any] = {"success": True, "object": obj}
            if object_type == "node" and args.get("include_neighbors"):
                out["neighbors"] = store.neighbors(
                    object_id, max_neighbors=int(args.get("max_neighbors") or 20)
                )
            if object_type == "node" and args.get("include_evidence"):
                out["evidence"] = store.list_evidence_for_node(object_id)
            return _json(out)
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_finalize(self, args: Optional[dict] = None, **_kw: Any) -> str:
        args = args or {}
        run_id = str(args.get("run_id") or "")
        if not run_id:
            return _json({"success": False, "error": "run_id required"})
        if self.store().get_run(run_id) is None:
            return _json({"success": False, "error": "run not found"})
        validate_only = bool(args.get("validate_only"))
        policy = str(args.get("promotion_policy") or "strict")
        try:
            promotion = {"changed": [], "count": 0}
            if policy == "strict" and not validate_only:
                promotion = _graph.promote_strict(self.store(), run_id)
            summary_id = None
            if args.get("create_summary", True) and not validate_only:
                summary = sanitize_text(
                    f"Finalized run {run_id}; promoted={promotion['count']}",
                    max_chars=2000,
                )
                summary_id = self.store().upsert_artifact(
                    {
                        "artifact_type": "run_summary",
                        "title": f"summary:{run_id}",
                        "content": summary.text,
                        "content_hash": _hash(summary.text),
                        "authority": "system",
                        "run_id": run_id,
                    }
                )["artifact_id"]
            if not validate_only:
                self.store().finalize_run(
                    run_id, summary_artifact_id=summary_id
                )
            return _json(
                {
                    "success": True,
                    "run_id": run_id,
                    "validate_only": validate_only,
                    "promotion": promotion,
                    "summary_artifact_id": summary_id,
                }
            )
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_evaluate_output(self, args: Optional[dict] = None, **_kw: Any) -> str:
        args = args or {}
        artifact_id = args.get("artifact_id")
        text = args.get("text")
        if bool(artifact_id) == bool(text):
            return _json(
                {
                    "success": False,
                    "error": "exactly one of artifact_id or text is required",
                }
            )
        try:
            if artifact_id:
                art = self.store().get_artifact(str(artifact_id))
                if art is None:
                    return _json({"success": False, "error": "artifact not found"})
                text = art.get("content") or ""
                target_id = str(artifact_id)
            else:
                cleaned = sanitize_text(
                    str(text), max_chars=self._config.max_artifact_chars
                )
                text = cleaned.text
                target_id = new_id()
            reference_nodes = []
            for node_id in args.get("reference_node_ids") or []:
                node = self.store().get_node(str(node_id))
                if node is not None:
                    reference_nodes.append(node)
            evaluation = self._inference.evaluate_output(
                text,
                criteria=args.get("criteria"),
                reference_nodes=reference_nodes,
            )
            evaluation_id = None
            if args.get("store_result", True):
                evaluation_id = self.store().insert_evaluation(
                    {
                        "run_id": args.get("run_id"),
                        "target_type": "artifact" if artifact_id else "text",
                        "target_id": target_id,
                        "evaluator_role": "output_evaluator",
                        "verdict": evaluation.get("verdict", "revise"),
                        "score": float(evaluation.get("overall_score") or 0),
                        "criteria": evaluation.get("criteria") or {},
                        "notes": json.dumps(
                            evaluation.get("claims") or [], ensure_ascii=False
                        )[:4000],
                        "suggested_revision": str(
                            evaluation.get("suggested_revision") or ""
                        )[:8000],
                    }
                )
            return _json(
                {
                    "success": True,
                    "evaluation": evaluation,
                    "evaluation_id": evaluation_id,
                    "artifact_rewritten": False,
                }
            )
        except SemanticGraphInferenceError as exc:
            return _json({"success": False, "error": str(exc)})
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_feedback(self, args: Optional[dict] = None, **_kw: Any) -> str:
        args = args or {}
        if args.get("user_confirmed") is not True:
            return _json({"success": False, "error": "user_confirmed must be true"})
        target_type = str(args.get("target_type") or "")
        target_id = str(args.get("target_id") or "")
        action = str(args.get("action") or "")
        reason = normalize_text(str(args.get("reason") or ""))
        if not target_type or not target_id or not action or not reason:
            return _json({"success": False, "error": "missing required fields"})
        if action not in {"accept", "reject", "supersede", "correct"}:
            return _json({"success": False, "error": f"unknown action: {action}"})
        try:
            store = self.store()
            if action == "accept" and target_type == "node":
                store.update_node_status(target_id, "accepted")
            elif action == "reject" and target_type == "node":
                store.update_node_status(target_id, "rejected")
            elif action == "reject" and target_type == "edge":
                store.update_edge_status(target_id, "rejected")
            elif action in {"supersede", "correct"} and target_type == "node":
                replacement = args.get("replacement")
                if action == "correct" and not isinstance(replacement, dict):
                    return _json(
                        {"success": False, "error": "replacement required for correct"}
                    )
                store.update_node_status(target_id, "superseded")
                new_id_value = None
                if isinstance(replacement, dict):
                    label = normalize_text(str(replacement.get("label") or reason))
                    new_id_value = _graph.make_node_id(
                        str(replacement.get("node_type") or "Claim"),
                        str(replacement.get("subtype") or ""),
                        str(replacement.get("identity_key") or ""),
                    )
                    store.upsert_node(
                        {
                            "node_id": new_id_value,
                            "node_type": replacement.get("node_type") or "Claim",
                            "subtype": replacement.get("subtype") or "",
                            "label": label,
                            "normalized_label": label.casefold(),
                            "summary": normalize_text(
                                str(replacement.get("summary") or reason)
                            ),
                            "identity_key": replacement.get("identity_key") or "",
                            "status": "asserted",
                            "authority": "user",
                            "confidence": float(replacement.get("confidence") or 0.9),
                            "salience": float(replacement.get("salience") or 0.8),
                            "metadata": sanitize_metadata(
                                {"correction_of": target_id, "reason": reason}
                            ),
                        }
                    )
                    edge_id = _graph.make_edge_id(
                        new_id_value, target_id, "supersedes", ""
                    )
                    store.upsert_edge(
                        {
                            "edge_id": edge_id,
                            "source_node_id": new_id_value,
                            "target_node_id": target_id,
                            "edge_type": "supersedes",
                            "relation_label": "",
                            "strength": 0.85,
                            "confidence": 0.9,
                            "status": "asserted",
                            "rationale": reason,
                        }
                    )
                return _json(
                    {
                        "success": True,
                        "action": action,
                        "old_id": target_id,
                        "new_id": new_id_value,
                    }
                )
            store.insert_event(
                {
                    "event_type": f"feedback_{action}",
                    "actor_type": "user",
                    "payload": {
                        "target_type": target_type,
                        "target_id": target_id,
                        "reason": reason,
                    },
                }
            )
            return _json({"success": True, "action": action, "target_id": target_id})
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    def handle_export(self, args: Optional[dict] = None, **_kw: Any) -> str:
        args = args or {}
        try:
            result = export_graph(
                self.store(),
                run_id=args.get("run_id"),
                format=str(args.get("format") or "json"),
                output_path=args.get("output_path"),
                include_artifacts=bool(args.get("include_artifacts")),
                include_rejected=bool(args.get("include_rejected")),
                export_root=self._config.export_root(),
            )
            return _json(result)
        except ExportPathError as exc:
            return _json({"success": False, "error": str(exc)})
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    # ------------------------------------------------------------------ hooks

    def on_pre_llm_call(self, **kwargs: Any) -> Optional[dict]:
        try:
            if not self._config.retrieval_enabled:
                return None
            message = str(
                kwargs.get("user_message")
                or kwargs.get("message")
                or kwargs.get("prompt")
                or ""
            )
            if len(message.strip()) < 2:
                return None
            hits = search_and_rank(
                self.store(),
                message,
                top_k=self._config.retrieval_top_k,
                min_confidence=self._config.min_recall_confidence,
                statuses=list(self._config.recall_statuses),
            )
            ctx = render_context(hits, self._config.retrieval_max_chars)
            if not ctx:
                return None
            return {"context": ctx}
        except Exception as exc:
            logger.warning("semantic-graph pre_llm_call failed open: %s", exc)
            return None

    def on_post_llm_call(self, **kwargs: Any) -> None:
        try:
            if not self._config.capture_turns:
                return
            user_message = str(kwargs.get("user_message") or "")
            assistant_response = str(kwargs.get("assistant_response") or "")
            if not assistant_response.strip():
                return
            session_id = str(kwargs.get("session_id") or "")
            turn_id = str(kwargs.get("turn_id") or kwargs.get("task_id") or new_id())
            model = str(kwargs.get("model") or "")
            platform = str(kwargs.get("platform") or "")
            store = self.store()
            for role, content, authority, atype in (
                ("user", user_message, "user", "user_message"),
                ("assistant", assistant_response, "assistant", "assistant_response"),
            ):
                if not content.strip():
                    continue
                cleaned = sanitize_text(
                    content, max_chars=self._config.max_artifact_chars
                )
                ch = _hash(cleaned.text)
                dedupe_key = f"{session_id}:{turn_id}:{atype}:{ch}"
                if dedupe_key in self._turn_seen:
                    continue
                self._turn_seen.add(dedupe_key)
                store.upsert_artifact(
                    {
                        "artifact_type": atype,
                        "title": f"{role}:{turn_id}",
                        "content": cleaned.text,
                        "content_hash": ch,
                        "authority": authority,
                        "session_id": session_id,
                        "turn_id": turn_id,
                        "model": model,
                        "platform": platform,
                        "truncated": cleaned.truncated,
                        "redaction_count": cleaned.redaction_count,
                    }
                )
            # Lightweight turn provenance nodes.
            user_node = _graph.make_node_id("Actor", "user", "user")
            asst_node = _graph.make_node_id("Actor", "assistant", "assistant")
            turn_node = _graph.make_node_id("Event", "Turn", f"{session_id}:{turn_id}")
            store.upsert_node(
                {
                    "node_id": user_node,
                    "node_type": "Actor",
                    "subtype": "user",
                    "label": "User",
                    "normalized_label": "user",
                    "summary": "Conversation user",
                    "identity_key": "user",
                    "status": "asserted",
                    "authority": "system",
                    "confidence": 1.0,
                    "salience": 0.2,
                }
            )
            store.upsert_node(
                {
                    "node_id": asst_node,
                    "node_type": "Actor",
                    "subtype": "assistant",
                    "label": "Assistant",
                    "normalized_label": "assistant",
                    "summary": "Conversation assistant",
                    "identity_key": "assistant",
                    "status": "asserted",
                    "authority": "system",
                    "confidence": 1.0,
                    "salience": 0.2,
                }
            )
            store.upsert_node(
                {
                    "node_id": turn_node,
                    "node_type": "Event",
                    "subtype": "Turn",
                    "label": f"Turn {turn_id}",
                    "normalized_label": normalize_text(f"turn {turn_id}").casefold(),
                    "summary": "Captured conversation turn",
                    "identity_key": f"{session_id}:{turn_id}",
                    "status": "asserted",
                    "authority": "system",
                    "confidence": 1.0,
                    "salience": 0.3,
                    "metadata": {"session_id": session_id, "model": model},
                }
            )
            if self._config.auto_extract == "all":
                try:
                    fragment = self._inference.extract_fragment(
                        json.dumps(
                            {
                                "user_message": user_message[:4000],
                                "assistant_response": assistant_response[:8000],
                            },
                            ensure_ascii=False,
                        )
                    )
                    run = store.create_run(
                        objective="auto_extract turn",
                        session_id=session_id,
                        turn_id=turn_id,
                        model=model,
                        platform=platform,
                    )
                    _graph.apply_fragment_to_store(
                        store,
                        run["run_id"],
                        fragment,
                        producer_role="auto_extract",
                        producer_type="plugin_llm",
                    )
                except Exception as exc:
                    logger.warning("semantic-graph auto_extract failed open: %s", exc)
        except Exception as exc:
            logger.warning("semantic-graph post_llm_call failed open: %s", exc)

    def on_post_tool_call(self, **kwargs: Any) -> None:
        try:
            if not self._config.capture_tool_events:
                return
            tool_name = str(kwargs.get("tool_name") or kwargs.get("name") or "")
            if not tool_name or tool_name in self._config.tool_capture_denylist:
                return
            if tool_name.startswith("semantic_graph_"):
                return
            args = kwargs.get("args") or kwargs.get("arguments") or {}
            result = kwargs.get("result") or kwargs.get("tool_result") or ""
            preview_limit = self._config.tool_result_preview_chars
            if tool_name in self._config.full_tool_result_allowlist:
                body = sanitize_text(str(result), max_chars=self._config.max_artifact_chars)
            else:
                body = sanitize_text(str(result), max_chars=preview_limit)
            args_clean = sanitize_text(
                json.dumps(args, ensure_ascii=False, default=str),
                max_chars=2000,
            )
            status = "error" if _looks_error(result) else "ok"
            self.store().insert_event(
                {
                    "event_type": "tool_call",
                    "actor_type": "tool",
                    "actor_id": tool_name,
                    "session_id": str(kwargs.get("session_id") or ""),
                    "turn_id": str(kwargs.get("turn_id") or ""),
                    "task_id": str(kwargs.get("task_id") or ""),
                    "payload": {
                        "tool_name": tool_name,
                        "status": status,
                        "args_sanitized": args_clean.text,
                        "result_preview": body.text,
                        "result_hash": _hash(body.text),
                        "duration_ms": kwargs.get("duration_ms"),
                        "tool_call_id": kwargs.get("tool_call_id"),
                    },
                }
            )
        except Exception as exc:
            logger.warning("semantic-graph post_tool_call failed open: %s", exc)

    def on_subagent_start(self, **kwargs: Any) -> None:
        try:
            if not self._config.capture_subagents:
                return
            goal = sanitize_text(
                str(kwargs.get("child_goal") or kwargs.get("goal") or ""),
                max_chars=500,
            )
            self.store().insert_event(
                {
                    "event_type": "subagent_start",
                    "actor_type": "subagent",
                    "actor_id": str(kwargs.get("child_subagent_id") or kwargs.get("subagent_id") or kwargs.get("task_id") or ""),
                    "session_id": str(kwargs.get("parent_session_id") or kwargs.get("session_id") or ""),
                    "turn_id": str(kwargs.get("parent_turn_id") or kwargs.get("turn_id") or ""),
                    "task_id": str(kwargs.get("child_subagent_id") or kwargs.get("task_id") or ""),
                    "payload": {
                        "parent_id": kwargs.get("parent_subagent_id") or kwargs.get("parent_id"),
                        "role": kwargs.get("child_role") or kwargs.get("role"),
                        "goal_preview": goal.text,
                        "model": kwargs.get("model"),
                    },
                }
            )
        except Exception as exc:
            logger.warning("semantic-graph subagent_start failed open: %s", exc)

    def on_subagent_stop(self, **kwargs: Any) -> None:
        try:
            if not self._config.capture_subagents:
                return
            summary = sanitize_text(
                str(kwargs.get("child_summary") or kwargs.get("summary") or kwargs.get("final_summary") or ""),
                max_chars=1000,
            )
            self.store().insert_event(
                {
                    "event_type": "subagent_stop",
                    "actor_type": "subagent",
                    "actor_id": str(kwargs.get("child_subagent_id") or kwargs.get("subagent_id") or kwargs.get("task_id") or ""),
                    "session_id": str(kwargs.get("child_session_id") or kwargs.get("session_id") or ""),
                    "turn_id": str(kwargs.get("parent_turn_id") or kwargs.get("turn_id") or ""),
                    "task_id": str(kwargs.get("child_subagent_id") or kwargs.get("task_id") or ""),
                    "payload": {
                        "status": kwargs.get("child_status") or kwargs.get("status"),
                        "duration_ms": kwargs.get("duration_ms", kwargs.get("duration")),
                        "summary_preview": summary.text,
                        "tool_call_history": sanitize_metadata(kwargs.get("tool_call_history") or []),
                    },
                }
            )
        except Exception as exc:
            logger.warning("semantic-graph subagent_stop failed open: %s", exc)

    def on_session_finalize(self, **_kwargs: Any) -> None:
        try:
            # Light retention check only — no VACUUM.
            days = self._config.retention_days
            if days <= 0:
                return
            # Intentionally no automatic purge; operator CLI owns deletion.
            logger.debug(
                "semantic-graph session finalize; retention_days=%s (no auto purge)",
                days,
            )
        except Exception as exc:
            logger.warning("semantic-graph on_session_finalize failed open: %s", exc)


def _looks_error(result: Any) -> bool:
    if isinstance(result, dict) and result.get("error"):
        return True
    text = str(result or "")
    try:
        data = json.loads(text)
        if isinstance(data, dict) and (data.get("error") or data.get("success") is False):
            return True
    except Exception:
        pass
    return False
