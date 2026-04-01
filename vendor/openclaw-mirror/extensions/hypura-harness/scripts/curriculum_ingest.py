"""Build merged JSONL curriculum from arXiv, SOUL.md, optional local JSONL, and quality gates.

Inspired by multi-source research flows; keeps attribution per row.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass
class IngestConfig:
    arxiv_ids: list[str] = field(default_factory=list)
    soul_path: Path | None = None
    extra_jsonl_paths: list[Path] = field(default_factory=list)
    min_chars: int = 80
    max_chars_per_record: int = 32000
    dedupe: bool = True


def _fetch_arxiv_atom(id_list: list[str]) -> str:
    if not id_list:
        return ""
    ids = ",".join(id_list)
    url = f"https://export.arxiv.org/api/query?id_list={ids}"
    req = urllib.request.Request(url, headers={"User-Agent": "hypura-harness/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def _parse_arxiv_entries(xml_text: str) -> list[dict[str, str]]:
    if not xml_text.strip():
        return []
    root = ET.fromstring(xml_text)
    entries: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", ARXIV_NS):
        title = (entry.find("atom:title", ARXIV_NS) or None)
        summary = (entry.find("atom:summary", ARXIV_NS) or None)
        id_el = (entry.find("atom:id", ARXIV_NS) or None)
        title_t = (title.text or "").strip() if title is not None else ""
        summary_t = re.sub(r"\s+", " ", (summary.text or "").strip()) if summary is not None else ""
        id_t = (id_el.text or "").strip() if id_el is not None else ""
        entries.append({"id": id_t, "title": title_t, "summary": summary_t})
    return entries


def _read_soul_chunks(path: Path, max_chunk: int = 4000) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks: list[str] = []
    for i in range(0, len(text), max_chunk):
        chunks.append(text[i : i + max_chunk].strip())
    return [c for c in chunks if len(c) >= 80]


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                logger.warning("skip bad jsonl line in %s", path.name)


def _normalize_record(
    instruction: str,
    output: str,
    source: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "instruction": instruction[:32000],
        "output": output[:32000],
        "source": source,
        "meta": meta,
    }


def _fingerprint(rec: dict[str, Any]) -> str:
    raw = (rec.get("instruction", "") + "\n" + rec.get("output", "")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def build_records(cfg: IngestConfig) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    # arXiv
    if cfg.arxiv_ids:
        xml = _fetch_arxiv_atom(cfg.arxiv_ids)
        for ent in _parse_arxiv_entries(xml):
            summ = ent.get("summary", "")
            if len(summ) < cfg.min_chars:
                continue
            instr = (
                f"Summarize and extract key technical claims from this paper entry.\n"
                f"Title: {ent.get('title', '')}\nURL: {ent.get('id', '')}"
            )
            out = summ[: cfg.max_chars_per_record]
            records.append(
                _normalize_record(
                    instr,
                    out,
                    "arxiv",
                    {"arxiv_id": ent.get("id", ""), "title": ent.get("title", "")},
                )
            )

    # SOUL.md → instruction-following style
    if cfg.soul_path and cfg.soul_path.exists():
        for idx, chunk in enumerate(_read_soul_chunks(cfg.soul_path)):
            records.append(
                _normalize_record(
                    "Follow the persona and protocol constraints in the following core document excerpt.",
                    chunk,
                    "soul",
                    {"path": "SOUL.md", "chunk_index": idx},
                )
            )

    # Extra JSONL (instruction/output or messages)
    for jp in cfg.extra_jsonl_paths:
        if not jp.exists():
            logger.warning("missing jsonl: %s", jp)
            continue
        for row in _iter_jsonl(jp):
            inst = str(row.get("instruction") or row.get("input") or "").strip()
            out = str(row.get("output") or row.get("response") or row.get("text") or "").strip()
            if isinstance(row.get("messages"), list):
                msgs = row["messages"]
                inst = json.dumps(msgs, ensure_ascii=False)[:8000]
                out = str(row.get("chosen", "") or row.get("content", "") or "")
            if not inst and not out:
                continue
            combined = (inst + "\n" + out).strip()
            if len(combined) < cfg.min_chars:
                continue
            records.append(
                _normalize_record(
                    inst or "(see output)",
                    out or combined,
                    "jsonl",
                    {"file": jp.name},
                )
            )

    if cfg.dedupe:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for r in records:
            fp = _fingerprint(r)
            if fp in seen:
                continue
            seen.add(fp)
            deduped.append(r)
        records = deduped

    return records


def write_jsonl(records: list[dict[str, Any]], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)
