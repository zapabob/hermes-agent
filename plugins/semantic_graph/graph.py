"""Graph fragment validation, IDs, merge, and promotion."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Optional

from .models import AUTHORITIES, EDGE_TYPES, NODE_TYPES, STATUSES, STRENGTH_LABELS
from .sanitize import normalize_key, normalize_text, sanitize_metadata, sanitize_text

RATIONALE_REQUIRED = frozenset({"supports", "contradicts", "caused_by", "supersedes"})
EVIDENCE_RELATIONS = frozenset({"supports", "contradicts", "mentions", "derived_from"})
MAX_FRAGMENT_BYTES = 128 * 1024
MAX_METADATA_BYTES = 8192


def stable_id(prefix: str, *parts: str) -> str:
    canonical = "\x1f".join(normalize_text(p) for p in parts)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_strength(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        key = value.strip().lower()
        if key in STRENGTH_LABELS:
            return STRENGTH_LABELS[key]
        try:
            return max(0.0, min(1.0, float(key)))
        except ValueError:
            return 0.5
    return 0.5


def make_node_id(node_type: str, subtype: str, identity_key: str) -> str:
    if identity_key:
        return stable_id("node", node_type, subtype or "", identity_key)
    return f"node_{uuid.uuid4().hex}"


def make_edge_id(
    source_id: str, target_id: str, edge_type: str, relation_label: str = ""
) -> str:
    return stable_id("edge", source_id, target_id, edge_type, relation_label or "")


def validate_fragment(
    fragment: dict[str, Any],
    store: Any,
    *,
    max_bytes: int = MAX_FRAGMENT_BYTES,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    raw = json.dumps(fragment, ensure_ascii=False)
    if len(raw.encode("utf-8")) > max_bytes:
        return {
            "valid": False,
            "errors": [f"fragment exceeds {max_bytes} bytes"],
            "warnings": [],
            "counts": {"nodes": 0, "edges": 0, "evidence": 0, "evaluations": 0},
        }

    if not isinstance(fragment, dict):
        return {
            "valid": False,
            "errors": ["fragment must be an object"],
            "warnings": [],
            "counts": {"nodes": 0, "edges": 0, "evidence": 0, "evaluations": 0},
        }

    nodes = fragment.get("nodes") or []
    edges = fragment.get("edges") or []
    evaluations = fragment.get("evaluations") or []
    if not isinstance(nodes, list) or not isinstance(edges, list):
        errors.append("nodes and edges must be arrays")

    temp_ids: set[str] = set()
    node_by_temp: dict[str, dict[str, Any]] = {}
    evidence_count = 0

    for i, node in enumerate(nodes if isinstance(nodes, list) else []):
        if not isinstance(node, dict):
            errors.append(f"nodes[{i}] must be object")
            continue
        tid = str(node.get("temp_id") or "")
        if not tid or not _valid_temp_id(tid):
            errors.append(f"nodes[{i}].temp_id invalid")
        elif tid in temp_ids:
            errors.append(f"duplicate temp_id: {tid}")
        else:
            temp_ids.add(tid)
            node_by_temp[tid] = node

        ntype = node.get("node_type")
        if ntype not in NODE_TYPES:
            errors.append(f"nodes[{i}].node_type invalid: {ntype}")
        status = node.get("status")
        if status not in STATUSES:
            errors.append(f"nodes[{i}].status invalid: {status}")
        authority = node.get("authority")
        if authority not in AUTHORITIES:
            errors.append(f"nodes[{i}].authority invalid: {authority}")
        conf = _num(node.get("confidence"), "nodes[{i}].confidence", errors)
        sal = _num(node.get("salience"), "nodes[{i}].salience", errors)
        label = normalize_text(str(node.get("label") or ""))
        if not label or len(label) > 500:
            errors.append(f"nodes[{i}].label invalid")

        meta = node.get("metadata") or {}
        if isinstance(meta, dict):
            meta_bytes = len(json.dumps(meta, ensure_ascii=False).encode("utf-8"))
            if meta_bytes > MAX_METADATA_BYTES:
                errors.append(f"nodes[{i}].metadata exceeds 8KB")
        else:
            errors.append(f"nodes[{i}].metadata must be object")

        evs = node.get("evidence") or []
        if not isinstance(evs, list):
            errors.append(f"nodes[{i}].evidence must be array")
            evs = []
        evidence_count += len(evs)
        has_exact_evidence = False
        for j, ev in enumerate(evs):
            ok, msg = _validate_evidence(ev, store)
            if not ok:
                errors.append(f"nodes[{i}].evidence[{j}]: {msg}")
            else:
                has_exact_evidence = True

        # Rule: assistant/subagent without evidence cannot be accepted.
        if (
            authority in {"assistant", "subagent", "tool", "external"}
            and status == "accepted"
            and not has_exact_evidence
        ):
            errors.append(
                f"nodes[{i}]: non-user accepted claim requires evidence"
            )
        if (
            authority in {"assistant", "subagent", "tool", "external"}
            and status == "asserted"
            and not has_exact_evidence
        ):
            warnings.append(
                f"nodes[{i}]: non-user asserted without evidence demoted conceptually"
            )

    for i, edge in enumerate(edges if isinstance(edges, list) else []):
        if not isinstance(edge, dict):
            errors.append(f"edges[{i}] must be object")
            continue
        src = str(edge.get("source_temp_id") or "")
        tgt = str(edge.get("target_temp_id") or "")
        if src not in node_by_temp:
            errors.append(f"edges[{i}]: unknown source_temp_id {src}")
        if tgt not in node_by_temp:
            errors.append(f"edges[{i}]: unknown target_temp_id {tgt}")
        if src and tgt and src == tgt:
            errors.append(f"edges[{i}]: self-loop rejected")
        et = edge.get("edge_type")
        if et not in EDGE_TYPES:
            errors.append(f"edges[{i}].edge_type invalid: {et}")
        st = edge.get("status")
        if st not in STATUSES:
            errors.append(f"edges[{i}].status invalid: {st}")
        _num(edge.get("confidence"), f"edges[{i}].confidence", errors)
        resolve_strength(edge.get("strength"))
        rationale = normalize_text(str(edge.get("rationale") or ""))
        if et in RATIONALE_REQUIRED and not rationale:
            errors.append(f"edges[{i}]: rationale required for {et}")
        evs = edge.get("evidence") or []
        if isinstance(evs, list):
            evidence_count += len(evs)
            for j, ev in enumerate(evs):
                if not isinstance(ev, dict):
                    continue
                ok, msg = _validate_evidence(ev, store)
                if not ok:
                    errors.append(f"edges[{i}].evidence[{j}]: {msg}")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "nodes": len(node_by_temp),
            "edges": len(edges) if isinstance(edges, list) else 0,
            "evidence": evidence_count,
            "evaluations": len(evaluations) if isinstance(evaluations, list) else 0,
        },
    }


def _valid_temp_id(tid: str) -> bool:
    import re

    return bool(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", tid))


def _num(value: Any, label: str, errors: list[str]) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be number")
        return 0.0
    if n < 0 or n > 1:
        errors.append(f"{label} must be in [0,1]")
    return max(0.0, min(1.0, n))


def _validate_evidence(ev: Any, store: Any) -> tuple[bool, str]:
    if not isinstance(ev, dict):
        return False, "must be object"
    artifact_id = str(ev.get("artifact_id") or "")
    if not artifact_id:
        return False, "artifact_id required"
    try:
        start = int(ev.get("start_char"))
        end = int(ev.get("end_char"))
    except (TypeError, ValueError):
        return False, "start/end must be integers"
    quote = str(ev.get("quote") or "")
    relation = ev.get("relation")
    if relation not in EVIDENCE_RELATIONS:
        return False, f"relation invalid: {relation}"
    try:
        conf = float(ev.get("confidence"))
    except (TypeError, ValueError):
        return False, "confidence must be number"
    if conf < 0 or conf > 1:
        return False, "confidence out of range"
    art = store.get_artifact(artifact_id) if store is not None else None
    if art is None:
        return False, f"artifact not found: {artifact_id}"
    content = art.get("content") or ""
    if not (0 <= start < end <= len(content)):
        return False, "offset out of range"
    if content[start:end] != quote:
        return False, "quote does not match artifact span"
    return True, ""


def apply_fragment_to_store(
    store: Any,
    run_id: str,
    fragment: dict[str, Any],
    *,
    producer_role: str,
    producer_type: str = "subagent",
    producer_id: str = "",
    model: str = "",
    fragment_id: Optional[str] = None,
) -> dict[str, Any]:
    """Apply a fragment atomically, including its deduplication row."""
    with store.transaction():
        return _apply_fragment_to_store(
            store,
            run_id,
            fragment,
            producer_role=producer_role,
            producer_type=producer_type,
            producer_id=producer_id,
            model=model,
            fragment_id=fragment_id,
        )


def _apply_fragment_to_store(
    store: Any,
    run_id: str,
    fragment: dict[str, Any],
    *,
    producer_role: str,
    producer_type: str = "subagent",
    producer_id: str = "",
    model: str = "",
    fragment_id: Optional[str] = None,
) -> dict[str, Any]:
    """Validate then apply. Invalid fragments are not partially committed."""
    result = validate_fragment(fragment, store)
    if not result["valid"]:
        return {"success": False, "validation": result}

    payload = json.dumps(fragment, ensure_ascii=False, sort_keys=True)
    payload_hash = content_hash(payload)
    frag_row = store.insert_fragment(
        {
            "fragment_id": fragment_id,
            "run_id": run_id,
            "producer_role": producer_role,
            "producer_type": producer_type,
            "producer_id": producer_id,
            "model": model,
            "payload_json": payload,
            "payload_hash": payload_hash,
        }
    )
    if frag_row.get("duplicate"):
        return {
            "success": True,
            "duplicate": True,
            "fragment_id": frag_row["fragment_id"],
            "validation": result,
        }

    temp_to_node: dict[str, str] = {}
    created_nodes: list[str] = []
    created_edges: list[str] = []

    for node in fragment.get("nodes") or []:
        identity_key = normalize_text(str(node.get("identity_key") or ""))
        subtype = normalize_text(str(node.get("subtype") or ""))
        label = normalize_text(str(node.get("label") or ""))
        node_id = make_node_id(node["node_type"], subtype, identity_key)
        # Demote unsupported non-user asserted/accepted to candidate.
        status = node.get("status", "candidate")
        authority = node.get("authority", "assistant")
        has_ev = bool(node.get("evidence"))
        if authority != "user" and status in {"accepted", "asserted"} and not has_ev:
            status = "candidate"
        store.upsert_node(
            {
                "node_id": node_id,
                "node_type": node["node_type"],
                "subtype": subtype,
                "label": label,
                "normalized_label": normalize_key(label),
                "summary": normalize_text(str(node.get("summary") or ""))[:4000],
                "identity_key": identity_key,
                "status": status,
                "authority": authority,
                "confidence": float(node.get("confidence", 0.5)),
                "salience": float(node.get("salience", 0.5)),
                "metadata": sanitize_metadata(node.get("metadata") or {}),
            }
        )
        store.link_run_node(run_id, node_id)
        temp_to_node[str(node["temp_id"])] = node_id
        created_nodes.append(node_id)
        for ev in node.get("evidence") or []:
            store.insert_evidence(
                {
                    "artifact_id": ev["artifact_id"],
                    "node_id": node_id,
                    "edge_id": None,
                    "relation": ev.get("relation", "supports"),
                    "start_char": int(ev["start_char"]),
                    "end_char": int(ev["end_char"]),
                    "quote": ev.get("quote", ""),
                    "quote_hash": content_hash(ev.get("quote", "")),
                    "confidence": float(ev.get("confidence", 0.5)),
                }
            )

    for edge in fragment.get("edges") or []:
        src = temp_to_node.get(str(edge.get("source_temp_id")))
        tgt = temp_to_node.get(str(edge.get("target_temp_id")))
        if not src or not tgt:
            continue
        relation_label = normalize_text(str(edge.get("relation_label") or ""))
        edge_id = make_edge_id(src, tgt, edge["edge_type"], relation_label)
        store.upsert_edge(
            {
                "edge_id": edge_id,
                "source_node_id": src,
                "target_node_id": tgt,
                "edge_type": edge["edge_type"],
                "relation_label": relation_label,
                "strength": resolve_strength(edge.get("strength")),
                "confidence": float(edge.get("confidence", 0.5)),
                "status": edge.get("status", "candidate"),
                "rationale": normalize_text(str(edge.get("rationale") or ""))[:2000],
                "metadata": sanitize_metadata(edge.get("metadata") or {}),
            }
        )
        store.link_run_edge(run_id, edge_id)
        created_edges.append(edge_id)
        for ev in edge.get("evidence") or []:
            if not isinstance(ev, dict):
                continue
            store.insert_evidence(
                {
                    "artifact_id": ev["artifact_id"],
                    "node_id": None,
                    "edge_id": edge_id,
                    "relation": ev.get("relation", "supports"),
                    "start_char": int(ev["start_char"]),
                    "end_char": int(ev["end_char"]),
                    "quote": ev.get("quote", ""),
                    "quote_hash": content_hash(ev.get("quote", "")),
                    "confidence": float(ev.get("confidence", 0.5)),
                }
            )

    for evl in fragment.get("evaluations") or []:
        if not isinstance(evl, dict):
            continue
        tid = str(evl.get("target_temp_id") or "")
        target_id = temp_to_node.get(tid, tid)
        store.insert_evaluation(
            {
                "run_id": run_id,
                "target_type": "node",
                "target_id": target_id,
                "evaluator_role": producer_role,
                "verdict": evl.get("verdict", "uncertain"),
                "score": float(evl.get("score", 0.0)),
                "criteria": evl.get("criteria") or {},
                "notes": str(evl.get("notes") or "")[:4000],
            }
        )

    return {
        "success": True,
        "duplicate": False,
        "fragment_id": frag_row["fragment_id"],
        "nodes": created_nodes,
        "edges": created_edges,
        "validation": result,
    }


def promote_strict(store: Any, run_id: str) -> dict[str, Any]:
    """Apply strict promotion policy over nodes linked to the run."""
    fragments = store.list_fragments_for_run(run_id)
    # Collect evaluator support/reject by target.
    support: set[str] = set()
    reject: set[str] = set()
    for frag in fragments:
        try:
            payload = json.loads(frag.get("payload_json") or "{}")
        except json.JSONDecodeError:
            continue
        for evl in payload.get("evaluations") or []:
            tid = str(evl.get("target_temp_id") or "")
            verdict = evl.get("verdict")
            if verdict in {"support", "pass"}:
                support.add(tid)
            if verdict in {"reject", "fail"}:
                reject.add(tid)

    nodes = store.list_nodes_for_run(run_id, limit=5000)
    evaluations = store.list_evaluations_for_run(run_id)
    for evaluation in evaluations:
        target_id = str(evaluation.get("target_id") or "")
        verdict = str(evaluation.get("verdict") or "")
        if target_id and verdict in {"support", "pass"}:
            support.add(target_id)
        if target_id and verdict in {"reject", "fail"}:
            reject.add(target_id)
    changed: list[dict[str, str]] = []
    for node in nodes:
        nid = node["node_id"]
        authority = node["authority"]
        conf = float(node["confidence"])
        status = node["status"]
        if status in {"rejected", "superseded"}:
            continue
        evs = store.list_evidence_for_node(nid)
        has_ev = bool(evs)
        new_status = status
        if authority == "user" and has_ev and conf >= 0.70:
            new_status = "asserted"
        elif authority != "user" and conf >= 0.75 and nid in support:
            new_status = "accepted"
        elif nid in reject:
            new_status = "rejected"
        elif not has_ev and authority != "user":
            new_status = "candidate"
        if new_status != status:
            store.update_node_status(nid, new_status)
            changed.append({"node_id": nid, "from": status, "to": new_status})
    return {"changed": changed, "count": len(changed)}
