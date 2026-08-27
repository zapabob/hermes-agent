#!/usr/bin/env python3
"""Generate a deterministic upstream-snapshot adoption report.

The helper never resolves a moving ref, fetches upstream, chooses a merge side,
or changes Git history. --apply writes deterministic report artifacts only;
semantic integration remains an explicit reviewed Git operation.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CAPTURED_AT_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})T")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\b")
DECISIONS = {
    "ADOPT",
    "COMPOSE",
    "REPLACE_DOWNSTREAM",
    "KEEP_DOWNSTREAM",
    "DEFER",
    "IGNORE",
}
CATEGORIES = {
    "SECURITY_CRITICAL",
    "DATA_INTEGRITY",
    "CREDENTIAL_BOUNDARY",
    "BUGFIX_RELEVANT",
    "WINDOWS_RELEVANT",
    "PUBLIC_API_CHANGE",
    "DESKTOP_API_CHANGE",
    "GATEWAY_API_CHANGE",
    "PLUGIN_API_CHANGE",
    "MODEL_PROVIDER_CHANGE",
    "FEATURE_OVERLAP",
    "FEATURE_NEW_RELEVANT",
    "TEST_INFRA",
    "DOCS_ONLY",
    "PLATFORM_IRRELEVANT",
}
SENSITIVE_TERMS = {
    "auth",
    "credential",
    "csrf",
    "encryption",
    "exfil",
    "permission",
    "sandbox",
    "secret",
    "security",
    "ssrf",
    "token",
    "traversal",
}
DATA_TERMS = {
    "atomic",
    "checkpoint",
    "compaction",
    "corrupt",
    "database",
    "dedup",
    "durable",
    "locking",
    "memory",
    "migration",
    "sqlite",
    "storage",
}
WINDOWS_TERMS = {
    "conpty",
    "crlf",
    "job object",
    "ntfs",
    "powershell",
    "win32",
    "windows",
    "winsock",
}


class SnapshotSyncError(RuntimeError):
    """The immutable snapshot contract was not satisfied."""


@dataclass(frozen=True)
class CommitRecord:
    sha: str
    subject: str
    paths: tuple[str, ...]
    intersections: tuple[str, ...]
    categories: tuple[str, ...]
    decision: str


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise SnapshotSyncError(f"git {' '.join(args)} failed: {detail}")
    return completed.stdout.strip()


def _resolve_commit(repo: Path, value: str, *, immutable: bool) -> str:
    if immutable and not SHA_RE.fullmatch(value):
        raise SnapshotSyncError("--upstream-sha must be an exact 40-character SHA")
    resolved = _git(repo, "rev-parse", "--verify", f"{value}^{{commit}}")
    if not SHA_RE.fullmatch(resolved):
        raise SnapshotSyncError(f"{value!r} did not resolve to a commit")
    if immutable and resolved != value:
        raise SnapshotSyncError(
            f"upstream substitution refused: requested {value}, resolved {resolved}"
        )
    return resolved


def _changed_paths(repo: Path, left: str, right: str) -> set[str]:
    output = _git(repo, "diff", "--name-only", f"{left}..{right}")
    return {line for line in output.splitlines() if line}


def _commit_paths(repo: Path, sha: str) -> tuple[str, ...]:
    output = _git(
        repo,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "-r",
        "-m",
        sha,
    )
    return tuple(sorted({line for line in output.splitlines() if line}))


def _display_path(path: str) -> str:
    if path.lower().startswith("contributors/emails/"):
        return "contributors/emails/[redacted]"
    return path


def _display_subject(subject: str) -> str:
    return EMAIL_RE.sub("[redacted-email]", subject)


def _is_docs_path(path: str) -> bool:
    lowered = path.lower()
    pure = PurePosixPath(lowered)
    return (
        lowered.startswith(("docs/", "_docs/", "contributors/"))
        or pure.suffix in {".md", ".rst"}
        or pure.name in {"license", "license.txt", "notice"}
    )


def _is_test_infra_path(path: str) -> bool:
    lowered = path.lower()
    return lowered.startswith(("tests/", "tests-js/", ".github/")) or lowered in {
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "uv.lock",
    }


def _platform_irrelevant(subject: str, paths: Sequence[str]) -> bool:
    text = f"{subject} {' '.join(paths)}".lower()
    foreign = any(
        term in text
        for term in ("darwin", "hyprland", "launchd", "macos", "wayland", "x11")
    )
    shared_or_windows = any(term in text for term in WINDOWS_TERMS) or any(
        not path.lower().startswith((
            "apps/bootstrap-installer/src-tauri/",
            "hermes_cli/macos_",
            "scripts/macos/",
        ))
        for path in paths
    )
    return foreign and not shared_or_windows


def _classify(
    subject: str,
    paths: Sequence[str],
    intersections: Sequence[str],
) -> tuple[tuple[str, ...], str]:
    text = f"{subject} {' '.join(paths)}".lower()
    categories: set[str] = set()
    if paths and all(_is_docs_path(path) for path in paths):
        categories.add("DOCS_ONLY")
    if paths and all(
        _is_test_infra_path(path) or _is_docs_path(path) for path in paths
    ):
        categories.add("TEST_INFRA")
    if any(term in text for term in SENSITIVE_TERMS):
        categories.add("SECURITY_CRITICAL")
    if any(
        term in text for term in {"credential", "keychain", "oauth", "secret", "token"}
    ):
        categories.add("CREDENTIAL_BOUNDARY")
    if any(term in text for term in DATA_TERMS):
        categories.add("DATA_INTEGRITY")
    if any(term in text for term in WINDOWS_TERMS) or any(
        path.lower().startswith("scripts/windows/") for path in paths
    ):
        categories.add("WINDOWS_RELEVANT")
    if any(path.lower().startswith("apps/desktop/") for path in paths):
        categories.add("DESKTOP_API_CHANGE")
    if any(path.lower().startswith("gateway/") for path in paths):
        categories.add("GATEWAY_API_CHANGE")
    if any("plugin" in path.lower() for path in paths):
        categories.add("PLUGIN_API_CHANGE")
    if any(
        term in text
        for term in (
            "bedrock",
            "gemini",
            "model provider",
            "nvidia",
            "openrouter",
            "provider",
        )
    ):
        categories.add("MODEL_PROVIDER_CHANGE")
    if any(term in text for term in (" api", "contract", "registry", "schema")):
        categories.add("PUBLIC_API_CHANGE")
    if intersections:
        categories.add("FEATURE_OVERLAP")
    if subject.lower().startswith(("fix", "perf")):
        categories.add("BUGFIX_RELEVANT")
    if subject.lower().startswith("feat"):
        categories.add("FEATURE_NEW_RELEVANT")
    if _platform_irrelevant(subject, paths):
        categories.add("PLATFORM_IRRELEVANT")
    if not categories:
        fallback = (
            "TEST_INFRA"
            if any(_is_test_infra_path(path) for path in paths)
            else "BUGFIX_RELEVANT"
        )
        categories.add(fallback)

    if "DOCS_ONLY" in categories and categories <= {"DOCS_ONLY", "TEST_INFRA"}:
        decision = "IGNORE"
    elif "PLATFORM_IRRELEVANT" in categories and categories <= {
        "PLATFORM_IRRELEVANT",
        "DESKTOP_API_CHANGE",
        "BUGFIX_RELEVANT",
        "FEATURE_NEW_RELEVANT",
    }:
        decision = "IGNORE"
    elif "FEATURE_OVERLAP" in categories:
        decision = "COMPOSE"
    elif categories & {
        "SECURITY_CRITICAL",
        "DATA_INTEGRITY",
        "CREDENTIAL_BOUNDARY",
        "PUBLIC_API_CHANGE",
        "BUGFIX_RELEVANT",
        "FEATURE_NEW_RELEVANT",
        "TEST_INFRA",
        "WINDOWS_RELEVANT",
    }:
        decision = "ADOPT"
    else:
        decision = "DEFER"

    if decision not in DECISIONS or not categories <= CATEGORIES:
        raise AssertionError("classifier emitted an unsupported value")
    return tuple(sorted(categories)), decision


def _collect_commits(
    repo: Path,
    merge_base: str,
    upstream_sha: str,
    fork_touched: set[str],
) -> list[CommitRecord]:
    output = _git(repo, "rev-list", "--reverse", f"{merge_base}..{upstream_sha}")
    commits: list[CommitRecord] = []
    for sha in (line for line in output.splitlines() if line):
        subject = _display_subject(_git(repo, "show", "-s", "--format=%s", sha))
        raw_paths = _commit_paths(repo, sha)
        raw_intersections = set(raw_paths) & fork_touched
        paths = tuple(sorted({_display_path(path) for path in raw_paths}))
        intersections = tuple(
            sorted({_display_path(path) for path in raw_intersections})
        )
        categories, decision = _classify(subject, paths, intersections)
        commits.append(
            CommitRecord(sha, subject, paths, intersections, categories, decision)
        )
    return commits


def _yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _yaml_sequence(values: Iterable[str], indent: int) -> list[str]:
    prefix = " " * indent
    materialized = list(values)
    if not materialized:
        return [f"{prefix}[]"]
    return [f"{prefix}- {_yaml_scalar(value)}" for value in materialized]


def _render_ledger(
    *,
    captured_at: str,
    upstream_repo: str,
    upstream_sha: str,
    downstream_sha: str,
    merge_base: str,
    commits: Sequence[CommitRecord],
    upstream_touched: Sequence[str],
    intersections: Sequence[str],
) -> str:
    category_counts = Counter(
        category for commit in commits for category in commit.categories
    )
    decision_counts = Counter(commit.decision for commit in commits)
    lines = [
        "schema_version: 1",
        f"captured_at: {_yaml_scalar(captured_at)}",
        f"upstream_repo: {_yaml_scalar(upstream_repo)}",
        f"upstream_head_sha: {_yaml_scalar(upstream_sha)}",
        f"downstream_start_sha: {_yaml_scalar(downstream_sha)}",
        f"merge_base_sha: {_yaml_scalar(merge_base)}",
        'scope_note: "Commits newer than upstream_head_sha are explicitly out of scope."',
        f"commit_count: {len(commits)}",
        f"touched_file_count: {len(upstream_touched)}",
        f"fork_intersection_count: {len(intersections)}",
        "category_counts:",
    ]
    lines.extend(
        f"  {category}: {category_counts.get(category, 0)}"
        for category in sorted(CATEGORIES)
    )
    lines.append("decision_counts:")
    lines.extend(
        f"  {decision}: {decision_counts.get(decision, 0)}"
        for decision in sorted(DECISIONS)
    )
    lines.append("fork_intersections:")
    lines.extend(_yaml_sequence(intersections, 2))
    lines.append("commits:")
    for commit in commits:
        lines.extend([
            f"  - sha: {_yaml_scalar(commit.sha)}",
            f"    subject: {_yaml_scalar(commit.subject)}",
            f"    decision: {commit.decision}",
            "    categories:",
        ])
        lines.extend(_yaml_sequence(commit.categories, 6))
        lines.append("    touched_paths:")
        lines.extend(_yaml_sequence(commit.paths, 6))
        lines.append("    fork_intersections:")
        lines.extend(_yaml_sequence(commit.intersections, 6))
    return "\n".join(lines) + "\n"


def _render_markdown(
    *,
    campaign_date: str,
    captured_at: str,
    upstream_sha: str,
    downstream_sha: str,
    merge_base: str,
    commits: Sequence[CommitRecord],
    upstream_touched: Sequence[str],
    intersections: Sequence[str],
) -> str:
    category_counts = Counter(
        category for commit in commits for category in commit.categories
    )
    decision_counts = Counter(commit.decision for commit in commits)
    category_table = "\n".join(
        f"| {category} | {category_counts.get(category, 0)} |"
        for category in sorted(CATEGORIES)
    )
    decision_table = "\n".join(
        f"| {decision} | {decision_counts.get(decision, 0)} |"
        for decision in sorted(DECISIONS)
    )
    intersection_list = "\n".join(f"- {path}" for path in intersections) or "- None"
    return f"""# Upstream snapshot integration, {campaign_date}

This report freezes the integration input. Commits newer than the recorded
upstream SHA are outside this campaign and must not be substituted.

## Snapshot

| Field | Value |
| --- | --- |
| Captured at | {captured_at} |
| Upstream head | {upstream_sha} |
| Downstream start | {downstream_sha} |
| Merge base | {merge_base} |
| Delta commits | {len(commits)} |
| Upstream-touched files | {len(upstream_touched)} |
| Fork intersections | {len(intersections)} |

## Decision counts

| Decision | Commits |
| --- | ---: |
{decision_table}

## Category counts

| Category | Commits |
| --- | ---: |
{category_table}

## Direct fork intersections

{intersection_list}

## Review boundary

UPSTREAM_ADOPTION.yaml is the commit-level authority. Decisions derive from
each commit subject, touched paths, and intersections with the downstream
delta. Semantic conflict resolution is excluded from this generator and must
preserve the policy files under .codex.
"""


def _render_snapshot(
    *,
    captured_at: str,
    upstream_repo: str,
    upstream_sha: str,
    downstream_sha: str,
    merge_base: str,
) -> str:
    payload = {
        "captured_at": captured_at,
        "upstream_repo": upstream_repo,
        "upstream_ref": "frozen commit supplied by operator",
        "upstream_head_sha": upstream_sha,
        "downstream_start_sha": downstream_sha,
        "merge_base_sha": merge_base,
        "scope_note": (
            "Commits newer than upstream_head_sha are explicitly out of scope."
        ),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-sha", required=True)
    parser.add_argument("--downstream-ref", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--report-only", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--captured-at")
    parser.add_argument(
        "--upstream-repo",
        default="https://github.com/NousResearch/hermes-agent.git",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.resolve()
    try:
        upstream_sha = _resolve_commit(repo, args.upstream_sha, immutable=True)
        downstream_sha = _resolve_commit(repo, args.downstream_ref, immutable=False)
        merge_base = _git(repo, "merge-base", downstream_sha, upstream_sha)
        fork_touched = _changed_paths(repo, merge_base, downstream_sha)
        upstream_touched = sorted(_changed_paths(repo, merge_base, upstream_sha))
        intersections = sorted({
            _display_path(path) for path in fork_touched & set(upstream_touched)
        })
        commits = _collect_commits(repo, merge_base, upstream_sha, fork_touched)
        captured_at = args.captured_at or "not-recorded"
        captured_at_match = CAPTURED_AT_RE.match(captured_at)
        if args.apply and args.captured_at and captured_at_match is None:
            raise SnapshotSyncError(
                "--captured-at must start with an ISO date (YYYY-MM-DD)"
            )
        campaign_date = (
            captured_at_match.group("date") if captured_at_match else "not-recorded"
        )
        campaign_slug = campaign_date.replace("-", "")
        ledger = _render_ledger(
            captured_at=captured_at,
            upstream_repo=args.upstream_repo,
            upstream_sha=upstream_sha,
            downstream_sha=downstream_sha,
            merge_base=merge_base,
            commits=commits,
            upstream_touched=upstream_touched,
            intersections=intersections,
        )
        report = _render_markdown(
            campaign_date=campaign_date,
            captured_at=captured_at,
            upstream_sha=upstream_sha,
            downstream_sha=downstream_sha,
            merge_base=merge_base,
            commits=commits,
            upstream_touched=upstream_touched,
            intersections=intersections,
        )
        snapshot = _render_snapshot(
            captured_at=captured_at,
            upstream_repo=args.upstream_repo,
            upstream_sha=upstream_sha,
            downstream_sha=downstream_sha,
            merge_base=merge_base,
        )
        payload = {
            "upstream_head_sha": upstream_sha,
            "downstream_start_sha": downstream_sha,
            "merge_base_sha": merge_base,
            "commit_count": len(commits),
            "touched_file_count": len(upstream_touched),
            "fork_intersection_count": len(intersections),
            "decisions": dict(
                sorted(Counter(commit.decision for commit in commits).items())
            ),
        }
        if args.report_only:
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if not args.captured_at:
            raise SnapshotSyncError(
                "--captured-at is required with --apply for deterministic output"
            )
        _write_if_changed(repo / ".codex" / "UPSTREAM_SNAPSHOT.json", snapshot)
        _write_if_changed(repo / "UPSTREAM_ADOPTION.yaml", ledger)
        _write_if_changed(
            repo / "_docs" / f"upstream-integration-{campaign_slug}.md",
            report,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except SnapshotSyncError as exc:
        print(f"snapshot_sync: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
