#!/usr/bin/env python3
"""Re-apply fork deltas on official_with_overlay paths after an upstream merge."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STRATEGY = REPO_ROOT / "scripts" / "merge_tools" / "hermes-merge-conflict-strategies.json"


def run(cmd: list[str], *, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _write_text_atomic(target: Path, text: str) -> None:
    """Write UTF-8 text via temp+replace to avoid Windows open() Errno 22 locks."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.overlay-tmp")
    # Normalize to LF; avoid pathlib newline= which can fail under file locks on Win.
    payload = text.replace("\r\n", "\n").encode("utf-8")
    tmp.write_bytes(payload)
    tmp.replace(target)


def overlay_path(path: str, upstream_ref: str, base_sha: str, old_head: str, *, sanitizers: dict) -> tuple[str, str]:
    from apply_three_way_overlay import three_way_merge, git_show

    code, merged = three_way_merge(path, base_sha, upstream_ref, old_head, sanitizers=sanitizers)
    if code == 2:
        # Prefer whichever side still exists (official-first when both missing → no-op).
        up_text = git_show(upstream_ref, path)
        fork_text = git_show(old_head, path)
        if up_text is not None:
            target = REPO_ROOT / path
            _write_text_atomic(target, up_text)
            run(["git", "add", "--", path])
            return path, "applied-upstream-fallback"
        if fork_text is not None:
            target = REPO_ROOT / path
            _write_text_atomic(target, fork_text)
            run(["git", "add", "--", path])
            return path, "applied-fork-fallback"
        return path, f"failed: missing version for {path}"
    if "<<<<<<<" in merged:
        # Official-first: keep upstream when favor-ours still leaves markers.
        up_text = git_show(upstream_ref, path)
        if up_text is None:
            return path, "conflict-markers"
        merged = up_text
        status = "applied-upstream-fallback"
    else:
        status = "applied"

    target = REPO_ROOT / path
    _write_text_atomic(target, merged)
    run(["git", "add", "--", path])
    return path, status


def load_overlay_paths(strategy_file: Path) -> list[str]:
    payload = json.loads(strategy_file.read_text(encoding="utf-8"))
    auto_overlay_paths = {
        str(path).replace("\\", "/")
        for path in payload.get("post_merge_auto_overlay_paths", [])
    }
    paths: list[str] = []
    for rule in payload.get("rules", []):
        pattern = str(rule.get("pattern", "")).replace("\\", "/")
        if rule.get("action") != "official_with_overlay" and pattern not in auto_overlay_paths:
            continue
        if "*" in pattern or "?" in pattern:
            continue
        paths.append(pattern)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply post-merge custom overlays.")
    parser.add_argument("--upstream-ref", default="upstream/main")
    parser.add_argument("--old-head", required=True)
    parser.add_argument("--merge-base", default="")
    parser.add_argument("--strategy-file", default=str(DEFAULT_STRATEGY))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    strategy_file = Path(args.strategy_file)
    if not strategy_file.is_absolute():
        strategy_file = (REPO_ROOT / strategy_file).resolve()

    merge_base = args.merge_base.strip() or run(
        ["git", "merge-base", args.old_head, args.upstream_ref],
    ).stdout.strip()
    if not merge_base:
        print("Could not resolve merge-base", file=sys.stderr)
        return 2

    paths = load_overlay_paths(strategy_file)
    strategy_payload = json.loads(strategy_file.read_text(encoding="utf-8"))
    from overlay_sanitize import load_overlay_sanitizers

    sanitizers = load_overlay_sanitizers(strategy_payload)
    failures: list[tuple[str, str]] = []
    for path in paths:
        result_path, status = overlay_path(
            path,
            args.upstream_ref,
            merge_base,
            args.old_head,
            sanitizers=sanitizers,
        )
        print(f"{result_path}: {status}")
        if status.startswith("failed") or status == "conflict-markers":
            failures.append((result_path, status))

    from merge_semantic_invariants import validate_repo

    invariant_failures = validate_repo(REPO_ROOT)
    for failure in invariant_failures:
        print(f"Semantic invariant failed: {failure}", file=sys.stderr)
    if invariant_failures:
        return 1

    if failures:
        print(f"\nOverlay failures: {len(failures)}", file=sys.stderr)
        return 1
    print(f"\nOverlay complete ({len(paths)} paths).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
