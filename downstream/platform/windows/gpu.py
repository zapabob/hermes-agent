"""Local NVIDIA device selection parsing without probing vendor services."""

from __future__ import annotations

import os


def visible_cuda_devices(value: str | None = None) -> tuple[int, ...]:
    """Parse CUDA_VISIBLE_DEVICES into an ordered tuple of numeric device ids."""
    raw = os.getenv("CUDA_VISIBLE_DEVICES", "") if value is None else value
    raw = raw.strip()
    if not raw or raw == "-1":
        return ()
    devices = tuple(int(part.strip()) for part in raw.split(","))
    if any(device < 0 for device in devices) or len(set(devices)) != len(devices):
        raise ValueError("CUDA device ids must be unique non-negative integers")
    return devices


__all__ = ["visible_cuda_devices"]
