from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Verdict(StrEnum):
    CLEAN = "CLEAN"
    UNKNOWN = "UNKNOWN"
    SUSPICIOUS = "SUSPICIOUS"
    MALICIOUS = "MALICIOUS"
    SCAN_ERROR = "SCAN_ERROR"


class EngineState(StrEnum):
    AVAILABLE = "available"
    SCANNER_UNAVAILABLE = "scanner_unavailable"
    SCAN_TIMEOUT = "scan_timeout"
    DATABASE_STALE = "database_stale"
    DATABASE_ERROR = "database_error"
    ENGINE_ERROR = "engine_error"


@dataclass(frozen=True)
class Finding:
    source: str
    name: str
    score: int
    state: EngineState = EngineState.AVAILABLE
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScanResult:
    path: str
    sha256: str
    size: int
    verdict: Verdict
    score: int
    action: str
    findings: tuple[Finding, ...]
    engine_versions: dict[str, str]
    cached: bool = False
    quarantine_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
