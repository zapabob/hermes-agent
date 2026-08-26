"""PowerShell and Git Bash boundary helpers."""

from __future__ import annotations

import re

_GIT_BASH_ALIAS = re.compile(r"^/[A-Za-z](?:/|$)")
_WSL_ALIAS = re.compile(r"^/mnt/[A-Za-z](?:/|$)")


def shell_path_kind(value: str) -> str:
    """Classify a native, MSYS, WSL, or relative shell path spelling."""
    raw = value.strip()
    if _WSL_ALIAS.match(raw):
        return "wsl"
    if _GIT_BASH_ALIAS.match(raw):
        return "msys"
    has_drive_root = (
        len(raw) >= 3 and raw[0].isalpha() and raw[1] == ":" and raw[2] in ("\\", "/")
    )
    if has_drive_root or raw.startswith("\\\\"):
        return "native"
    return "relative"


def quote_powershell_literal(value: str) -> str:
    """Quote one PowerShell literal argument without invoking a shell parser."""
    return "'" + value.replace("'", "''") + "'"


__all__ = ["quote_powershell_literal", "shell_path_kind"]
