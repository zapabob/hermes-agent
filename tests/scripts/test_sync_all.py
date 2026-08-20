"""Tests for scripts/sync_all.py argument handling."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_sync_all_module():
    spec = importlib.util.spec_from_file_location("sync_all", REPO_ROOT / "scripts" / "sync_all.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_allow_preflight_blockers_flag_defaults_false():
    sync_all = load_sync_all_module()

    args = sync_all.parse_args(["--merge"])

    assert args.allow_preflight_blockers is False


def test_allow_preflight_blockers_flag_can_be_enabled():
    sync_all = load_sync_all_module()

    args = sync_all.parse_args(["--merge", "--allow-preflight-blockers"])

    assert args.allow_preflight_blockers is True


@pytest.mark.parametrize(
    "argv",
    [
        ["--dry-run", "--merge"],
        ["--dry-run", "--openclaw-execute"],
    ],
)
def test_dry_run_rejects_write_capable_modes(argv):
    sync_all = load_sync_all_module()

    with pytest.raises(SystemExit) as exc_info:
        sync_all.parse_args(argv)

    assert exc_info.value.code == 2


def test_collect_blockers_includes_unresolved_conflicts(tmp_path):
    sync_all = load_sync_all_module()
    report_path = tmp_path / "resolver-report.json"
    report_path.write_text(
        json.dumps(
            {
                "blocked_paths": ["manual.py"],
                "unresolved_conflicts": ["conflicted.py"],
            },
        ),
        encoding="utf-8",
    )

    assert sync_all._collect_blockers(report_path) == ["manual.py", "conflicted.py"]
