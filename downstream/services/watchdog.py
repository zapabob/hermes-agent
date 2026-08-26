"""Single outer restart-authority contract."""

from __future__ import annotations

from . import RestartRequest

OUTER_RESTART_AUTHORITY = "scripts/windows/watchdog-go"


def request_restart(service: str, reason: str) -> RestartRequest:
    """Create a restart request; execution remains owned by the Go watchdog."""
    if not service.strip() or not reason.strip():
        raise ValueError("Restart requests require service and reason")
    return RestartRequest(service=service, reason=reason)


def owns_automatic_restart(component: str) -> bool:
    """Return true only for the designated external supervisor."""
    return component.replace("\\", "/").rstrip("/") == OUTER_RESTART_AUTHORITY


__all__ = ["OUTER_RESTART_AUTHORITY", "owns_automatic_restart", "request_restart"]
