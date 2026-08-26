"""Deterministic Windows path normalization across native and shell aliases."""

from __future__ import annotations

import re
from os import PathLike
from pathlib import PureWindowsPath

_MSYS_DRIVE = re.compile(r"^/([A-Za-z])(?:/(.*))?$")
_WSL_DRIVE = re.compile(r"^/mnt/([A-Za-z])(?:/(.*))?$")


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


__all__ = ["normalize_windows_path", "windows_path_key"]
