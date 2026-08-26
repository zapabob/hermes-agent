"""Local llama.cpp observation contract; restart execution belongs to watchdog."""

from . import HealthEndpoint

LLAMA_HEALTH = HealthEndpoint("llama", "http://127.0.0.1:8080", "/health")

__all__ = ["LLAMA_HEALTH"]
