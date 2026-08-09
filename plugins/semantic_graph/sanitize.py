"""Secret redaction and text normalization for semantic-graph storage."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|secret|password|passwd|authorization|cookie|session)"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s`\"']+)"
)
# Match the complete header before generic assignment patterns can consume its
# key.  A partial header redaction is a storage violation because the value may
# still be recoverable from the remaining text.
BEARER_RE = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+")
JSON_SECRET_RE = re.compile(
    r"(?i)([\"'](?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|secret|password|passwd|authorization|cookie|session)[\"']\s*:\s*)([\"'][^\"']*[\"']|[^,}\s]+)"
)
ASSIGN_SECRET_RE = re.compile(
    r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|secret|password|passwd|authorization|cookie|session)\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
)
LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")
EMAIL_RE = re.compile(r"\b[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}\b")
WIN_HOME_RE = re.compile(r"C:\\Users\\[^\\\s`\"]+", re.I)
MSYS_HOME_RE = re.compile(r"C:/Users/[^\s`\"]+", re.I)
IP_RE = re.compile(
    r"\b(?:10|127|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b"
)
# Bidirectional / invisible controls (keep common whitespace).
INVISIBLE_RE = re.compile(
    r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F"
    r"\u200B-\u200F\u202A-\u202E\u2060-\u2064\u2066-\u206F\uFEFF]"
)

_MAX_METADATA_BYTES = 8192


@dataclass(frozen=True)
class SanitizedText:
    text: str
    redaction_count: int
    truncated: bool


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = " ".join(text.split())
    return text.strip()


def normalize_key(value: str) -> str:
    return normalize_text(value).casefold()


def _redact(text: str) -> tuple[str, int]:
    count = 0

    def _bump(m: re.Match[str], replacement: str) -> str:
        nonlocal count
        count += 1
        return replacement

    # Consume a complete bearer header before the core generic assignment
    # redactor can split it into a key and a trailing value.
    text = BEARER_RE.sub(lambda m: _bump(m, f"{m.group(1)}[REDACTED]"), text)

    # Use Hermes' central redactor first at this persistence boundary. The
    # plugin-specific passes below cover PII and remain available in minimal
    # environments where the core module cannot be imported.
    try:
        from agent.redact import redact_sensitive_text
        core_text = redact_sensitive_text(text, force=True, file_read=True)
        if core_text != text:
            count += 1
        text = core_text
    except Exception:
        pass

    text = BEARER_RE.sub(lambda m: _bump(m, f"{m.group(1)}[REDACTED]"), text)
    text = JSON_SECRET_RE.sub(lambda m: _bump(m, f"{m.group(1)}[REDACTED]"), text)
    text = ASSIGN_SECRET_RE.sub(lambda m: _bump(m, f"{m.group(1)}[REDACTED]"), text)
    text = SECRET_RE.sub(lambda m: _bump(m, f"{m.group(1)}=[REDACTED]"), text)
    text = EMAIL_RE.sub(lambda m: _bump(m, "[EMAIL_REDACTED]"), text)
    text = WIN_HOME_RE.sub(lambda m: _bump(m, "~"), text)
    text = MSYS_HOME_RE.sub(lambda m: _bump(m, "~"), text)
    text = IP_RE.sub(lambda m: _bump(m, "[PRIVATE_IP_REDACTED]"), text)
    text = LONG_TOKEN_RE.sub(lambda m: _bump(m, "[LONG_TOKEN_REDACTED]"), text)
    return text, count


def sanitize_text(text: str, *, max_chars: int) -> SanitizedText:
    raw = str(text or "").replace("\x00", "")
    raw = INVISIBLE_RE.sub("", raw)
    redacted, count = _redact(raw)
    truncated = False
    if max_chars > 0 and len(redacted) > max_chars:
        redacted = redacted[: max(0, max_chars - 1)] + "…"
        truncated = True
    return SanitizedText(text=redacted, redaction_count=count, truncated=truncated)


def sanitize_value(value: Any, *, max_chars: int = 4000, depth: int = 0) -> Any:
    """Sanitize arbitrary persistence-bound values without changing primitives."""
    if depth > 6:
        return "[TRUNCATED_DEPTH]"
    if isinstance(value, str):
        return sanitize_text(value, max_chars=max_chars).text
    if isinstance(value, dict):
        return {
            sanitize_text(str(k), max_chars=128).text: sanitize_value(
                v, max_chars=max_chars, depth=depth + 1
            )
            for k, v in list(value.items())[:64]
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_value(v, max_chars=max_chars, depth=depth + 1) for v in list(value)[:64]]
    return value


def sanitize_metadata(value: Any, *, max_bytes: int = _MAX_METADATA_BYTES) -> dict[str, Any]:
    """Recursively sanitize a metadata mapping and enforce a byte budget."""

    def _walk(obj: Any, depth: int = 0) -> Any:
        if depth > 6:
            return "[TRUNCATED_DEPTH]"
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for i, (k, v) in enumerate(obj.items()):
                if i >= 64:
                    out["__truncated__"] = True
                    break
                key = normalize_text(str(k))[:128]
                out[key] = _walk(v, depth + 1)
            return out
        if isinstance(obj, (list, tuple)):
            items = [_walk(x, depth + 1) for x in list(obj)[:64]]
            if len(obj) > 64:
                items.append("[TRUNCATED_LIST]")
            return items
        if isinstance(obj, (int, float, bool)) or obj is None:
            return obj
        cleaned = sanitize_text(str(obj), max_chars=2000)
        return cleaned.text

    if not isinstance(value, dict):
        value = {}
    cleaned = _walk(value)
    if not isinstance(cleaned, dict):
        cleaned = {}
    encoded = json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > max_bytes:
        return {"__error__": "metadata_too_large", "bytes": len(encoded.encode("utf-8"))}
    return cleaned
