"""Watchdog-managed Desktop backend observation contract."""

from . import HealthEndpoint

DESKTOP_BACKEND_HEALTH = HealthEndpoint(
    "desktop-backend", "http://127.0.0.1:9119", "/api/status"
)

__all__ = ["DESKTOP_BACKEND_HEALTH"]
