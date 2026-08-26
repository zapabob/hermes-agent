#!/usr/bin/env python3
"""Validate downstream policy ledgers and repository boundaries."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from downstream import UPSTREAM_SNAPSHOT_SHA  # noqa: E402
from downstream.features import validate_feature_manifest  # noqa: E402

_REQUIRED_SNAPSHOT_FIELDS = {
    "captured_at",
    "upstream_repo",
    "upstream_ref",
    "upstream_head_sha",
    "downstream_start_sha",
    "merge_base_sha",
}
_REQUIRED_CARRY_FIELDS = {
    "id",
    "upstream_paths",
    "downstream_reason",
    "invariants",
    "tests",
    "integration_policy",
}
_REQUIRED_FILES = (
    ".codex/SOP.md",
    ".codex/WINDOWS_PLATFORM_CONTRACT.md",
    ".codex/FORK_INVARIANTS.md",
    ".codex/UPSTREAM_POLICY.md",
    ".codex/UPSTREAM_SNAPSHOT.json",
    "DOWNSTREAM_POLICY.md",
    "_docs/carry-surface-20260826.json",
    "_docs/carry-surface-20260826.md",
    "_docs/repository-rename-20260826.md",
    "FEATURES.yaml",
    "CARRY.yaml",
)


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a mapping")
    return data


def _check_paths(entries: list[dict[str, Any]], field: str, label: str) -> list[str]:
    errors: list[str] = []
    for entry in entries:
        entry_id = entry.get("id", "unknown")
        values = entry.get(field)
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list) or not values:
            errors.append(f"{label} {entry_id}: {field} must be non-empty")
            continue
        for value in values:
            if not isinstance(value, str) or not (ROOT / value).exists():
                errors.append(f"{label} {entry_id}: missing {field} path {value}")
    return errors


def validate_repository() -> list[str]:
    """Return all policy errors in deterministic order."""
    errors = [
        f"missing required file: {path}"
        for path in _REQUIRED_FILES
        if not (ROOT / path).is_file()
    ]
    if errors:
        return sorted(errors)

    snapshot = json.loads(
        (ROOT / ".codex/UPSTREAM_SNAPSHOT.json").read_text(encoding="utf-8")
    )
    missing_snapshot = sorted(_REQUIRED_SNAPSHOT_FIELDS - snapshot.keys())
    if missing_snapshot:
        errors.append(f"snapshot missing: {', '.join(missing_snapshot)}")
    if snapshot.get("upstream_head_sha") != UPSTREAM_SNAPSHOT_SHA:
        errors.append("snapshot SHA differs from frozen downstream constant")
    if "out of scope" not in str(snapshot.get("scope_note", "")).lower():
        errors.append("snapshot scope_note must exclude newer upstream commits")

    features = _load_yaml(ROOT / "FEATURES.yaml")
    errors.extend(validate_feature_manifest(features))
    feature_entries = features.get("features", [])
    if isinstance(feature_entries, list):
        typed_features = [entry for entry in feature_entries if isinstance(entry, dict)]
        errors.extend(_check_paths(typed_features, "owner_path", "feature"))
        errors.extend(_check_paths(typed_features, "tests", "feature"))
    if features.get("snapshot_sha") != UPSTREAM_SNAPSHOT_SHA:
        errors.append("FEATURES.yaml snapshot_sha differs from frozen snapshot")

    carry = _load_yaml(ROOT / "CARRY.yaml")
    carry_entries = carry.get("carry")
    if not isinstance(carry_entries, list) or not carry_entries:
        errors.append("CARRY.yaml carry must be a non-empty list")
    else:
        for index, entry in enumerate(carry_entries):
            if not isinstance(entry, dict):
                errors.append(f"carry[{index}] must be a mapping")
                continue
            missing = sorted(_REQUIRED_CARRY_FIELDS - entry.keys())
            if missing:
                errors.append(f"carry[{index}] missing: {', '.join(missing)}")
        typed_carry = [entry for entry in carry_entries if isinstance(entry, dict)]
        errors.extend(_check_paths(typed_carry, "upstream_paths", "carry"))
        errors.extend(_check_paths(typed_carry, "tests", "carry"))
    if carry.get("snapshot_sha") != UPSTREAM_SNAPSHOT_SHA:
        errors.append("CARRY.yaml snapshot_sha differs from frozen snapshot")

    if (ROOT / "platform").exists():
        errors.append("top-level platform package is forbidden")

    return sorted(set(errors))


def main() -> int:
    errors = validate_repository()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Downstream policy validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
