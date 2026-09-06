"""Deterministic Windows path normalization across native and shell aliases."""

from __future__ import annotations

import re
from os import PathLike
from pathlib import PureWindowsPath

_MSYS_DRIVE = re.compile(r"^/([A-Za-z])(?:/(.*))?$")
_WSL_DRIVE = re.compile(r"^/mnt/([A-Za-z])(?:/(.*))?$")
# Drive-letter shell spellings only. Must not match /home, /tmp, etc.
_SHELL_DRIVE = re.compile(r"^/(?:(?:cygdrive|mnt)/)?([A-Za-z])(/.*)?$")


def translate_msys_drive_path(value: str | PathLike[str]) -> str | None:
    """Translate MSYS / Cygwin / WSL drive spellings to a native Windows path.

    Returns ``None`` when *value* is not a single-letter drive alias so callers
    can leave ``/home/...``, native ``C:\\...``, and relative paths unchanged.
    Unlike :func:`normalize_windows_path`, this never runs unmatched inputs
    through ``PureWindowsPath`` (which would rewrite ``/home/x`` on Windows).
    """
    raw = str(value)
    match = _SHELL_DRIVE.match(raw)
    if not match:
        return None
    drive = match.group(1).upper()
    tail = (match.group(2) or "").replace("/", "\\")
    return f"{drive}:{tail or chr(92)}"


def normalize_windows_path(value: str | PathLike[str]) -> str:
    """Return a native Windows spelling for C:/, /c/, or /mnt/c/ inputs."""
    raw = str(value).strip()
    if not raw:
        raise ValueError("Windows path must not be empty")
    match = _WSL_DRIVE.match(raw) or _MSYS_DRIVE.match(raw)
    if match:
        drive, tail = match.groups()
        raw = f"{drive.upper()}:/{tail or ''}"
    return str(PureWindowsPath(raw))


def windows_path_key(value: str | PathLike[str]) -> str:
    """Return a case-insensitive comparison key without touching the filesystem."""
    return normalize_windows_path(value).casefold()


__all__ = [
    "normalize_windows_path",
    "translate_msys_drive_path",
    "windows_path_key",
]
