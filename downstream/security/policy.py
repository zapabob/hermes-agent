from __future__ import annotations

from .models import EngineState, Finding, Verdict


def decide(findings: list[Finding], allowed: bool) -> tuple[Verdict, int, str, str | None]:
    score = max((finding.score for finding in findings), default=0)
    error_states = {
        EngineState.SCAN_TIMEOUT,
        EngineState.DATABASE_ERROR,
        EngineState.ENGINE_ERROR,
    }
    authoritative_available = any(
        finding.source in {"clamav", "yara"} and finding.state == EngineState.AVAILABLE
        for finding in findings
    )
    authoritative_unavailable = any(
        finding.source in {"clamav", "yara"} and finding.state == EngineState.SCANNER_UNAVAILABLE
        for finding in findings
    )
    errors = [finding for finding in findings if finding.state in error_states]
    if errors:
        return Verdict.SCAN_ERROR, score, "blocked_pending_review", errors[0].name
    if score >= 80:
        action = "allowlisted" if allowed else "quarantine"
        return Verdict.MALICIOUS, score, action, None
    if score >= 20:
        return Verdict.SUSPICIOUS, score, "warn", None
    if authoritative_unavailable and not authoritative_available:
        return Verdict.SCAN_ERROR, 0, "blocked_pending_review", "authoritative scanners unavailable"
    if authoritative_available:
        return Verdict.CLEAN, 0, "allow", None
    return Verdict.UNKNOWN, 0, "allow_with_unknown_verdict", None
