from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/fork-cicd.yml"
SCHEDULED = ROOT / ".github/workflows/windows-full-qualification.yml"


def _workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _step_commands(job: dict) -> str:
    return "\n".join(str(step.get("run", "")) for step in job.get("steps", []))


def test_required_tier_one_jobs_exist() -> None:
    jobs = _workflow(WORKFLOW)["jobs"]
    assert set(jobs) == {
        "downstream-policy",
        "windows-native-python",
        "windows-native-desktop",
        "windows-watchdog-go",
        "upstream-api-compat",
        "windows-regression",
        "security-locks",
    }


def test_policy_lane_fetches_frozen_upstream_history() -> None:
    checkout = _workflow(WORKFLOW)["jobs"]["downstream-policy"]["steps"][0]
    assert checkout["with"]["fetch-depth"] == 0


def test_all_tier_one_jobs_run_natively_on_windows() -> None:
    workflow = _workflow(WORKFLOW)
    jobs = workflow["jobs"]
    assert workflow["defaults"]["run"]["shell"] == "pwsh"
    assert all(job["runs-on"] == "windows-latest" for job in jobs.values())
    commands = "\n".join(_step_commands(job) for job in jobs.values())
    assert "/dev/null" not in commands
    assert "$RUNNER_TEMP/" not in commands
    assert "test ! -d" not in commands
    assert "test -d" not in commands


def test_native_jobs_cover_windows_contracts() -> None:
    jobs = _workflow(WORKFLOW)["jobs"]
    assert jobs["windows-native-python"]["runs-on"] == "windows-latest"
    assert jobs["windows-native-desktop"]["runs-on"] == "windows-latest"
    assert jobs["windows-watchdog-go"]["runs-on"] == "windows-latest"
    assert "tests/downstream/test_windows_contracts.py" in _step_commands(
        jobs["windows-native-python"]
    )
    assert "tests/gateway/test_async_session_db.py" in _step_commands(
        jobs["windows-native-python"]
    )
    assert "go test ./..." in _step_commands(jobs["windows-watchdog-go"])
    assert "GOOS=windows" not in _step_commands(jobs["windows-watchdog-go"])


def test_desktop_lane_derives_metadata_and_builds() -> None:
    job = _workflow(WORKFLOW)["jobs"]["windows-native-desktop"]
    commands = _step_commands(job)
    assert "package.engines.node" in commands
    assert "package-lock.json" in commands
    assert "npm ci" in commands
    assert "run typecheck" in commands
    assert "run lint" in commands
    assert "run test:desktop:platforms" in commands
    assert "run build" in commands


def test_security_lane_checks_all_lock_ecosystems() -> None:
    commands = _step_commands(_workflow(WORKFLOW)["jobs"]["security-locks"])
    assert "uv lock --check" in commands
    assert "uv export --frozen --all-extras --no-dev --no-emit-project" in commands
    assert "Join-Path $env:RUNNER_TEMP 'hermes-audit-requirements.txt'" in commands
    assert "pip-audit==2.10.1 pip-audit --require-hashes --disable-pip --requirement" in commands
    assert "npm audit" in commands
    assert "go mod verify" in commands


def test_scheduled_full_windows_qualification_exists() -> None:
    workflow = _workflow(SCHEDULED)
    jobs = workflow["jobs"]
    assert set(jobs) == {"python-full", "desktop-full", "watchdog-live"}
    assert all(job["runs-on"] == "windows-latest" for job in jobs.values())
    assert "scripts/run_tests_parallel.py" in _step_commands(jobs["python-full"])


def test_external_actions_are_commit_pinned() -> None:
    action = re.compile(r"^([^./][^@]*)@([0-9a-f]{40})$")
    for path in (WORKFLOW, SCHEDULED):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            reference = stripped.removeprefix("uses:").split("#", 1)[0].strip()
            assert action.match(reference), (
                f"unpinned action in {path.name}: {reference}"
            )
