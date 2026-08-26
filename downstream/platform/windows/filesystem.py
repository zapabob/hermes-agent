"""Bounded retry policy for NTFS sharing violations."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Sequence
from os import PathLike

DEFAULT_REPLACE_DELAYS = (0.025, 0.05, 0.1, 0.2)
_WINDOWS_RETRY_ERRORS = frozenset({5, 32, 33})


def _is_sharing_violation(exc: OSError) -> bool:
    return (
        isinstance(exc, PermissionError)
        or getattr(exc, "winerror", None) in _WINDOWS_RETRY_ERRORS
    )


def replace_with_retry(
    source: str | PathLike[str],
    destination: str | PathLike[str],
    *,
    delays: Sequence[float] = DEFAULT_REPLACE_DELAYS,
    replace: Callable[[str | PathLike[str], str | PathLike[str]], None] = os.replace,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Atomically replace a path, retrying only recognized Windows lock errors."""
    for attempt in range(len(delays) + 1):
        try:
            replace(source, destination)
            return
        except OSError as exc:
            if not _is_sharing_violation(exc) or attempt >= len(delays):
                raise
            sleep(float(delays[attempt]))


__all__ = ["DEFAULT_REPLACE_DELAYS", "replace_with_retry"]
