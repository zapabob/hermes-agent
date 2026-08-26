"""Windows process helpers that retain official Hermes process authority."""

from __future__ import annotations

import subprocess

from agent.deadline import kill_process_tree as _official_kill_process_tree


def kill_process_tree(pid: int) -> bool:
    """Delegate process-tree termination to the official Hermes implementation."""
    if pid <= 0:
        return False
    return _official_kill_process_tree(pid)


def windows_creation_flags(*, detached: bool = False, no_window: bool = True) -> int:
    """Build native child flags without assuming constants exist on POSIX hosts."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if no_window else 0
    if detached:
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return flags


__all__ = ["kill_process_tree", "windows_creation_flags"]
