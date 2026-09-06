"""Non-overridable browser authority boundaries."""

from __future__ import annotations

from urllib.parse import urlsplit

_PERSONAL_SESSION_HOSTS = frozenset(
    {"twitter.com", "x.com", "youtu.be", "youtube.com"}
)


def is_personal_session_url(raw_url: str) -> bool:
    """Return whether only the operator's OS-browser session may open a URL."""
    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return False
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return any(
        hostname == host or hostname.endswith(f".{host}")
        for host in _PERSONAL_SESSION_HOSTS
    )
