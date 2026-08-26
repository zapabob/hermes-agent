"""Windows updater primitives for locked runtime artifacts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from os import PathLike

from .filesystem import DEFAULT_REPLACE_DELAYS, replace_with_retry


def handoff_locked_artifact(
    staged: str | PathLike[str],
    live: str | PathLike[str],
    *,
    delays: Sequence[float] = DEFAULT_REPLACE_DELAYS,
    replace: Callable | None = None,
) -> None:
    """Atomically hand a staged artifact to the live path with bounded retries."""
    kwargs = {"delays": delays}
    if replace is not None:
        kwargs["replace"] = replace
    replace_with_retry(staged, live, **kwargs)


__all__ = ["handoff_locked_artifact"]
