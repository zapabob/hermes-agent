from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sync-hermes-operational-scripts.py"
LLAMA_HOTSWAP = Path(__file__).resolve().parents[2] / "scripts" / "windows" / "start-llama-hotswap.ps1"


def run_sync(repo_root: Path, hermes_home: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo_root),
            "--hermes-home",
            str(hermes_home),
            *arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def allowlist() -> list[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--list"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["allowlist"]


def seed_repo(repo_root: Path) -> list[str]:
    scripts = repo_root / "scripts"
    scripts.mkdir(parents=True)
    names = allowlist()
    for name in names:
        (scripts / name).write_text(f"# {name}\n", encoding="utf-8")
    return names


def summary(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_llama_hotswap_uses_the_current_windows_profile_for_default_paths() -> None:
    script = LLAMA_HOTSWAP.read_text(encoding="utf-8")

    assert "C:\\Users\\" not in script
    assert "$env:USERPROFILE" in script


def test_apply_reconciles_only_the_reviewed_allowlist(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    hermes_home = tmp_path / "hermes-home"
    names = seed_repo(repo_root)
    unmanaged = hermes_home / "scripts" / "unmanaged.py"
    unmanaged.parent.mkdir(parents=True)
    unmanaged.write_text("private state\n", encoding="utf-8")

    deployed = run_sync(repo_root, hermes_home, "--apply")

    assert deployed.returncode == 0, deployed.stderr
    deployed_summary = summary(deployed)
    assert deployed_summary["deployed_to_hermes"] == names
    report_path = hermes_home / "sync-reports" / "latest-operational-script-sync.json"
    assert report_path.is_file()
    assert json.loads(report_path.read_text(encoding="utf-8"))["report_written"] is True
    assert unmanaged.read_text(encoding="utf-8") == "private state\n"

    checked = run_sync(repo_root, hermes_home, "--check")
    assert checked.returncode == 0, checked.stderr
    assert summary(checked)["unchanged"] == names


def test_check_detects_drift_and_apply_restores_repository_copy(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    hermes_home = tmp_path / "hermes-home"
    names = seed_repo(repo_root)
    assert run_sync(repo_root, hermes_home, "--apply").returncode == 0

    drifted = hermes_home / "scripts" / names[0]
    drifted.write_text("local modification\n", encoding="utf-8")

    check = run_sync(repo_root, hermes_home, "--check")
    assert check.returncode == 1
    assert summary(check)["drift"] == [names[0]]

    repaired = run_sync(repo_root, hermes_home, "--apply")
    assert repaired.returncode == 0
    assert (repo_root / "scripts" / names[0]).read_bytes() == drifted.read_bytes()


def test_bootstrap_requires_an_explicit_apply_opt_in(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    hermes_home = tmp_path / "hermes-home"
    names = seed_repo(repo_root)
    imported_name = names[-1]
    (repo_root / "scripts" / imported_name).unlink()
    deployed_source = hermes_home / "scripts" / imported_name
    deployed_source.parent.mkdir(parents=True)
    deployed_source.write_text("reviewed deployed script\n", encoding="utf-8")

    no_import = run_sync(repo_root, hermes_home, "--apply")
    assert no_import.returncode == 1
    assert imported_name in summary(no_import)["missing_repo"]

    imported = run_sync(repo_root, hermes_home, "--apply", "--bootstrap-from-hermes")
    assert imported.returncode == 0, imported.stderr
    assert summary(imported)["imported_to_repo"] == [imported_name]
    assert (repo_root / "scripts" / imported_name).read_bytes() == deployed_source.read_bytes()
