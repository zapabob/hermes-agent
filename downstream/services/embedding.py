"""Local embedding observation contract; restart execution belongs to watchdog."""

from . import HealthEndpoint

EMBEDDING_HEALTH = HealthEndpoint("embedding", "http://127.0.0.1:8082", "/health")

__all__ = ["EMBEDDING_HEALTH"]
