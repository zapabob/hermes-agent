"""Namespaced Windows named-pipe identifiers."""

from __future__ import annotations

import re

_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9_.-]+")


def named_pipe_path(name: str, *, profile: str = "default") -> str:
    """Return a deterministic profile-scoped Hermes named-pipe path."""
    safe_name = _SAFE_COMPONENT.sub("-", name.strip()).strip("-.")
    safe_profile = _SAFE_COMPONENT.sub("-", profile.strip()).strip("-.")
    if not safe_name or not safe_profile:
        raise ValueError("Pipe name and profile must contain a safe character")
    return rf"\.\pipe\hermes-{safe_profile}-{safe_name}"


__all__ = ["named_pipe_path"]
