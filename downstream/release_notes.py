from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

import yaml


DOWNSTREAM_TAG = re.compile(r"^v\d+\.\d+\.\d+-win\.\d+$")


def _read_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def resolve_previous_downstream_tag(repo_root: Path, current_tag: str) -> str | None:
    tags = _git(
        repo_root,
        "tag",
        "--merged",
        "HEAD",
        "--list",
        "v*.*.*-win.*",
        "--sort=-version:refname",
    ).splitlines()
    return next(
        (tag for tag in tags if tag != current_tag and DOWNSTREAM_TAG.fullmatch(tag)),
        None,
    )


def read_commit_history(
    repo_root: Path, previous_tag: str | None
) -> list[dict[str, Any]]:
    if not previous_tag:
        return []
    raw = _git(repo_root, "log", "--format=%H%x1f%s", f"{previous_tag}..HEAD")
    commits: list[dict[str, Any]] = []
    for line in raw.splitlines():
        sha, separator, subject = line.partition("\x1f")
        if not separator:
            continue
        paths = _git(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            sha,
        ).splitlines()
        commits.append({"sha": sha, "subject": subject, "paths": paths})
    return commits


def _matches(commit: dict[str, Any], terms: tuple[str, ...]) -> bool:
    text = " ".join([
        str(commit.get("subject", "")),
        *map(str, commit.get("paths", [])),
    ]).lower()
    return any(term in text for term in terms)


def _commit_lines(commits: list[dict[str, Any]], terms: tuple[str, ...]) -> list[str]:
    selected = [commit for commit in commits if _matches(commit, terms)]
    if not selected:
        return ["- No categorized changes in this release range."]
    return [f"- `{str(commit['sha'])[:12]}` {commit['subject']}" for commit in selected]


def render_release_notes(
    *,
    manifest: dict[str, Any],
    features: dict[str, Any],
    carry: dict[str, Any],
    adoption: dict[str, Any],
    snapshot: dict[str, Any],
    commits: list[dict[str, Any]],
    previous_tag: str | None,
) -> str:
    verified_windows_features = sorted(
        str(feature.get("id"))
        for feature in features.get("features", [])
        if isinstance(feature, dict)
        and feature.get("status") == "verified"
        and feature.get("windows_required") is True
    )
    carry_count = len([
        entry for entry in carry.get("carry", []) if isinstance(entry, dict)
    ])
    category_counts = adoption.get("category_counts", {})
    critical_count = int(category_counts.get("SECURITY_CRITICAL", 0))
    upstream_sha = str(
        snapshot.get("upstream_head_sha") or manifest["upstream_snapshot_sha"]
    )
    signing = "Signed" if manifest["installer_signed"] else "Unsigned"
    real_workstation = manifest["windows_qualification"].get(
        "real_workstation_qualified", False
    )
    lines = [
        f"# {manifest['product_name']} {manifest['downstream_version']}",
        "",
        "This is an unofficial Windows-first downstream distribution of Hermes Agent.",
        "It is not affiliated with or endorsed by Nous Research.",
        "",
        f"Release channel: {manifest['release_channel']}",
        f"Downstream commit: `{manifest['downstream_commit_sha']}`",
        f"Frozen upstream snapshot: `{upstream_sha}`",
        f"Windows CI qualification: {manifest['windows_qualification']['status']}",
        f"Real workstation qualification: {'passed' if real_workstation else 'not qualified'}",
        f"Installer signature: {signing}",
        f"Provenance attestation: {manifest['attestation_status']}",
        "",
        "## Windows Workstation changes",
        "",
        f"Verified Windows-required capabilities: {', '.join(verified_windows_features)}.",
        f"Direct upstream-file carry entries: {carry_count}.",
        "",
        *_commit_lines(
            commits,
            (
                "windows",
                "installer",
                "portable",
                "watchdog",
                "distribution",
                "release",
            ),
        ),
        "",
        "## Upstream snapshot",
        "",
        f"This release is based on exact upstream commit `{upstream_sha}`.",
        f"Adoption decisions: {json.dumps(adoption.get('decision_counts', {}), sort_keys=True)}.",
        "Commits after that frozen snapshot are outside this release train.",
        "",
        "## Security",
        "",
        f"The frozen upstream audit classified {critical_count} commits as security-critical.",
        *_commit_lines(
            commits,
            ("security", "cve", "credential", "approval", "auth", "lock"),
        ),
        "",
        "## Bug fixes",
        "",
        *_commit_lines(commits, ("fix", "bug", "regression")),
        "",
        "## Local AI",
        "",
        *_commit_lines(
            commits,
            ("llama", "gguf", "embedding", "local-ai", "local_provider", "model"),
        ),
        "",
        "## Desktop",
        "",
        *_commit_lines(commits, ("apps/desktop", "electron", "desktop")),
        "",
        "## Memory",
        "",
        *_commit_lines(
            commits, ("memory", "semantic_graph", "semantic-graph", "ebbinghaus")
        ),
        "",
        "## Voice / VR / Unity",
        "",
        *_commit_lines(commits, ("voice", "tts", "vrchat", "unity", "aituber")),
        "",
        "## Known limitations",
        "",
        f"- Installer Authenticode status: {signing}.",
        f"- Physical workstation qualification: {'passed' if real_workstation else 'not recorded as passed'}.",
        "- GGUF model weights are not included in the default release artifacts.",
        (
            f"- Changes are measured from downstream tag `{previous_tag}`."
            if previous_tag
            else "- No earlier downstream Windows tag is recorded; this is the first release range."
        ),
        "",
        "## Artifact hashes",
        "",
    ]
    for artifact in manifest["artifacts"]:
        lines.append(f"- `{artifact['sha256']}`  `{artifact['name']}`")
    lines.extend([
        "",
        "Verify downloads against `SHA256SUMS.txt` before installation.",
        "Updates resolve only from the downstream repository and selected release channel.",
        "",
    ])
    return "\n".join(lines)


def build_release_notes(
    manifest: dict[str, Any], repo_root: Path, previous_tag: str | None = None
) -> str:
    current_tag = f"v{manifest['downstream_version']}"
    baseline_tag = previous_tag or resolve_previous_downstream_tag(
        repo_root, current_tag
    )
    return render_release_notes(
        manifest=manifest,
        features=_read_yaml(repo_root / "FEATURES.yaml"),
        carry=_read_yaml(repo_root / "CARRY.yaml"),
        adoption=_read_yaml(repo_root / "UPSTREAM_ADOPTION.yaml"),
        snapshot=json.loads(
            (repo_root / ".codex" / "UPSTREAM_SNAPSHOT.json").read_text(
                encoding="utf-8"
            )
        ),
        commits=read_commit_history(repo_root, baseline_tag),
        previous_tag=baseline_tag,
    )
