"""Safe graph export to JSON / JSONL / Markdown."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .sanitize import sanitize_text


class ExportPathError(ValueError):
    pass


def _safe_filename(stem: str, fmt: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "export"
    ext = {"json": "json", "jsonl": "jsonl", "markdown": "md"}[fmt]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{cleaned}_{stamp}.{ext}"


def _resolve_output_path(
    output_path: Optional[str],
    *,
    export_root: Path,
    fmt: str,
    run_id: Optional[str],
) -> Path:
    export_root = export_root.resolve()
    export_root.mkdir(parents=True, exist_ok=True)
    if not output_path:
        return export_root / _safe_filename(run_id or "semantic_graph", fmt)
    candidate = Path(output_path)
    if not candidate.is_absolute():
        candidate = export_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(export_root)
    except ValueError as exc:
        raise ExportPathError(
            f"output_path escapes export root: {resolved} not under {export_root}"
        ) from exc
    return resolved


def export_graph(
    store: Any,
    *,
    run_id: Optional[str] = None,
    format: str = "json",
    output_path: Optional[str] = None,
    include_artifacts: bool = False,
    include_rejected: bool = False,
    export_root: Optional[Path] = None,
) -> dict[str, Any]:
    fmt = (format or "json").lower()
    if fmt not in {"json", "jsonl", "markdown"}:
        raise ValueError(f"unsupported format: {format}")
    if export_root is None:
        raise ValueError("export_root required")

    statuses = None if include_rejected else ["asserted", "accepted", "candidate"]
    if run_id:
        nodes = store.list_nodes_for_run(run_id, statuses=statuses, limit=5000)
        edges = store.list_edges_for_run(
            run_id, include_rejected=include_rejected, limit=10000
        )
    else:
        nodes = store.list_nodes(statuses=statuses, limit=5000) if statuses else store.list_nodes(limit=5000)
        edges = store.list_edges(include_rejected=include_rejected, limit=10000)
    if not include_rejected:
        nodes = [n for n in nodes if n.get("status") not in {"rejected", "superseded"}]
    payload: dict[str, Any] = {
        "run_id": run_id,
        "nodes": nodes,
        "edges": edges,
    }
    if include_artifacts:
        arts = store.list_artifacts(run_id=run_id, limit=2000)
        for art in arts:
            cleaned = sanitize_text(art.get("content") or "", max_chars=12000)
            art["content"] = cleaned.text
        payload["artifacts"] = arts

    path = _resolve_output_path(
        output_path, export_root=export_root, fmt=fmt, run_id=run_id
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
    elif fmt == "jsonl":
        lines = []
        for node in nodes:
            lines.append(json.dumps({"type": "node", **node}, ensure_ascii=False))
        for edge in edges:
            lines.append(json.dumps({"type": "edge", **edge}, ensure_ascii=False))
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    else:
        md = ["# Semantic Graph Export", ""]
        if run_id:
            md.append(f"Run: `{run_id}`")
            md.append("")
        md.append("## Nodes")
        for node in nodes:
            md.append(
                f"- **{node.get('node_type')}** `{node.get('node_id')}` "
                f"[{node.get('status')}] {node.get('label')}"
            )
        md.append("")
        md.append("## Edges")
        for edge in edges:
            md.append(
                f"- `{edge.get('source_node_id')}` —[{edge.get('edge_type')}]→ "
                f"`{edge.get('target_node_id')}`"
            )
        path.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    return {
        "success": True,
        "path": str(path),
        "format": fmt,
        "nodes": len(nodes),
        "edges": len(edges),
    }
