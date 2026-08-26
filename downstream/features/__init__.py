"""Validation helpers for the downstream product capability ledger."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REQUIRED_FIELDS = frozenset({
    "id",
    "status",
    "owner_path",
    "public_surface",
    "upstream_touch",
    "tests",
    "windows_required",
    "upstream_equivalent",
    "integration_policy",
})


def load_feature_manifest(path: Path | None = None) -> dict[str, Any]:
    """Load FEATURES.yaml from the repository root."""
    manifest_path = path or Path(__file__).resolve().parents[2] / "FEATURES.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("FEATURES.yaml must contain a mapping")
    return data


def validate_feature_manifest(data: dict[str, Any]) -> list[str]:
    """Return deterministic schema errors without changing repository state."""
    errors: list[str] = []
    features = data.get("features")
    if not isinstance(features, list) or not features:
        return ["features must be a non-empty list"]
    seen: set[str] = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            errors.append(f"features[{index}] must be a mapping")
            continue
        missing = sorted(_REQUIRED_FIELDS - feature.keys())
        if missing:
            errors.append(f"features[{index}] missing: {', '.join(missing)}")
        feature_id = feature.get("id")
        if not isinstance(feature_id, str) or not feature_id:
            errors.append(f"features[{index}].id must be a non-empty string")
        elif feature_id in seen:
            errors.append(f"duplicate feature id: {feature_id}")
        else:
            seen.add(feature_id)
        tests = feature.get("tests")
        if not isinstance(tests, list) or not tests:
            errors.append(f"{feature_id or index}.tests must be a non-empty list")
    return errors


__all__ = ["load_feature_manifest", "validate_feature_manifest"]
