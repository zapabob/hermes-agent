from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOWNSTREAM = "zapabob/hermes-agent-windows"
UPSTREAM = "NousResearch/hermes-agent"
OLD_DOWNSTREAM = re.compile("zapabob/" + r"hermes-agent(?!-windows)")
HISTORICAL_ALLOWLIST = {
    "_docs/2026-06-29_upstream-security-sync-main_Codex.md",
    "_docs/2026-08-21_cicd-allgreen-and-lmcache-verification_antigravity.md",
    "_docs/implementation-log-20260603-hermes-upstream-security-sync.md",
    "_docs/repository-rename-20260826.md",
    "docs/benchmarks/desktop-model-switch-handoff-2026-08-20.md",
    "docs/benchmarks/desktop-model-switch-implementation-log-2026-08-20.md",
    "fork/local-workspace/notes/TASK_SUMMARY.md",
}


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_package_metadata_owned_by_downstream() -> None:
    root_package = json.loads(text("package.json"))
    desktop_package = json.loads(text("apps/desktop/package.json"))
    assert DOWNSTREAM in root_package["repository"]["url"]
    assert root_package["bugs"]["url"] == f"https://github.com/{DOWNSTREAM}/issues"
    assert root_package["homepage"] == f"https://github.com/{DOWNSTREAM}#readme"
    assert DOWNSTREAM in desktop_package["repository"]["url"]


def test_downstream_user_links_use_renamed_repository() -> None:
    for path in (
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/setup_help.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "apps/desktop/README.md",
        "apps/desktop/src/app/settings/about-settings.tsx",
        "website/docusaurus.config.ts",
    ):
        assert DOWNSTREAM in text(path), path
    assert "https://hermes-agent.nousresearch.com/" not in text(
        "apps/desktop/src/app/settings/about-settings.tsx"
    )


def test_old_downstream_slug_only_remains_in_historical_evidence() -> None:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    offenders: list[str] = []
    for path in result.stdout.splitlines():
        candidate = ROOT / path
        try:
            content = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if OLD_DOWNSTREAM.search(content) and path not in HISTORICAL_ALLOWLIST:
            offenders.append(path)
    assert offenders == []


def test_upstream_and_runtime_identifiers_remain_official() -> None:
    assert f"https://github.com/{UPSTREAM}.git" in text("hermes_cli/update_cmd.py")
    assert UPSTREAM in text(".codex/UPSTREAM_SNAPSHOT.json")
    assert (
        "module github.com/nousresearch/hermes-agent/scripts/windows/watchdog-go"
        in text("scripts/windows/watchdog-go/go.mod")
    )
    assert re.search(r"^hermes\s*=", text("pyproject.toml"), re.MULTILINE)
