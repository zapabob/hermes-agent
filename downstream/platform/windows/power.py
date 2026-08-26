"""Sleep/resume gap classification independent of wall-clock changes."""

from __future__ import annotations


def resume_gap_detected(
    previous_monotonic: float, current_monotonic: float, *, threshold_seconds: float
) -> bool:
    """Return whether a monotonic sample gap exceeds the configured threshold."""
    if threshold_seconds <= 0:
        raise ValueError("threshold_seconds must be positive")
    if current_monotonic < previous_monotonic:
        return True
    return current_monotonic - previous_monotonic >= threshold_seconds


__all__ = ["resume_gap_detected"]
