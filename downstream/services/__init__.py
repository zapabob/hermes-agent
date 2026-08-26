"""Side-effect-free contracts for downstream long-lived services."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class HealthEndpoint:
    name: str
    base_url: str
    health_path: str

    def url(self) -> str:
        parsed = urlsplit(self.base_url)
        if parsed.scheme != "http" or parsed.hostname not in {
            "127.0.0.1",
            "::1",
            "localhost",
        }:
            raise ValueError(f"{self.name} endpoint must use loopback HTTP")
        return self.base_url.rstrip("/") + "/" + self.health_path.lstrip("/")


@dataclass(frozen=True)
class RestartRequest:
    service: str
    reason: str


__all__ = ["HealthEndpoint", "RestartRequest"]
