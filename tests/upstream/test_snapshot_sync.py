from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "upstream" / "snapshot_sync.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("snapshot_sync", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


@pytest.fixture
def divergent_repo(tmp_path: Path) -> tuple[Path, str, str]:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.name", "Snapshot Test")
    _git(tmp_path, "config", "user.email", "snapshot@example.invalid")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "base.txt")
    _git(tmp_path, "commit", "-m", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")

    (tmp_path / "fork.txt").write_text("fork\n", encoding="utf-8")
    _git(tmp_path, "add", "fork.txt")
    _git(tmp_path, "commit", "-m", "feat: downstream")
    downstream = _git(tmp_path, "rev-parse", "HEAD")

    _git(tmp_path, "checkout", "--detach", base)
    (tmp_path / "upstream.txt").write_text("upstream\n", encoding="utf-8")
    _git(tmp_path, "add", "upstream.txt")
    _git(tmp_path, "commit", "-m", "fix: upstream")
    upstream = _git(tmp_path, "rev-parse", "HEAD")
    return tmp_path, downstream, upstream


def test_report_only_is_deterministic_and_read_only(
    divergent_repo: tuple[Path, str, str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_module()
    repo, downstream, upstream = divergent_repo
    args = [
        "--repo",
        str(repo),
        "--upstream-sha",
        upstream,
        "--downstream-ref",
        downstream,
        "--report-only",
    ]

    assert module.main(args) == 0
    first = capsys.readouterr().out
    assert module.main(args) == 0
    second = capsys.readouterr().out

    assert first == second
    assert '"commit_count": 1' in first
    assert not (repo / "UPSTREAM_ADOPTION.yaml").exists()
    assert not (repo / "_docs" / "upstream-integration-20260826.md").exists()


def test_apply_writes_only_reports(
    divergent_repo: tuple[Path, str, str],
) -> None:
    module = _load_module()
    repo, downstream, upstream = divergent_repo

    result = module.main([
        "--repo",
        str(repo),
        "--upstream-sha",
        upstream,
        "--downstream-ref",
        downstream,
        "--captured-at",
        "2026-08-26T18:25:00+09:00",
        "--apply",
    ])

    assert result == 0
    ledger = (repo / "UPSTREAM_ADOPTION.yaml").read_text(encoding="utf-8")
    assert f'upstream_head_sha: "{upstream}"' in ledger
    assert "commit_count: 1" in ledger
    assert _git(repo, "rev-parse", "HEAD") == upstream


def test_moving_upstream_ref_is_rejected(
    divergent_repo: tuple[Path, str, str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_module()
    repo, downstream, _ = divergent_repo

    result = module.main([
        "--repo",
        str(repo),
        "--upstream-sha",
        "HEAD",
        "--downstream-ref",
        downstream,
        "--report-only",
    ])

    assert result == 2
    assert "exact 40-character SHA" in capsys.readouterr().err


def test_sensitive_intersection_requires_composition() -> None:
    module = _load_module()

    categories, decision = module._classify(
        "fix(auth): preserve credential boundary",
        ["gateway/auth.py"],
        ["gateway/auth.py"],
    )

    assert decision == "COMPOSE"
    assert "SECURITY_CRITICAL" in categories
    assert "CREDENTIAL_BOUNDARY" in categories
    assert "FEATURE_OVERLAP" in categories
