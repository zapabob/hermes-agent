#!/usr/bin/env python3
"""Merge NousResearch/hermes-agent (upstream/main) into a local sync branch.

Typical fork workflow:
  1. Ensure ``git remote add upstream https://github.com/NousResearch/hermes-agent.git``
  2. ``py -3 scripts/sync_upstream.py --dry-run`` — fetch + divergence summary
  3. ``py -3 scripts/sync_upstream.py --merge`` — create ``sync/upstream-YYYYMMDD`` and merge
  4. Resolve conflicts (see WATCHLIST_PATHS), then ``py -3 scripts/sync_upstream.py --pytest-only``

Conflict-prone Windows / shell files are listed in WATCHLIST_PATHS for quick review.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_REMOTE = "upstream"
UPSTREAM_REF = f"{UPSTREAM_REMOTE}/main"

# Files to highlight when merging; keep in sync with fork documentation.
WATCHLIST_PATHS = (
    "tools/environments/local.py",
    "tools/environments/persistent_shell.py",
    "tools/environments/platform_shell_compat.py",
    "README.md",
)

DEFAULT_PYTEST_TARGETS = (
    "tests/tools/test_local_persistent.py",
    "tests/tools/test_local_env_blocklist.py",
)


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


def _git_ok(*args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], check=False)


def _require_git_repo() -> None:
    p = _git_ok("rev-parse", "--git-dir")
    if p.returncode != 0:
        print("error: not a git repository", file=sys.stderr)
        sys.exit(2)


def _working_tree_clean() -> bool:
    p = _git_ok("diff-index", "--quiet", "HEAD", "--")
    return p.returncode == 0


def _upstream_configured() -> bool:
    p = _git_ok("remote", "get-url", UPSTREAM_REMOTE)
    return p.returncode == 0


def _print_summary() -> None:
    print("--- merge-base ---")
    mb = _git_ok("merge-base", "HEAD", UPSTREAM_REF)
    if mb.returncode != 0:
        print(mb.stderr.strip() or mb.stdout.strip() or "merge-base failed")
        return
    base = mb.stdout.strip()
    print(base)

    print("\n--- commits on upstream/main not in HEAD (first 25) ---")
    log = _git_ok(
        "log", "--oneline", f"HEAD..{UPSTREAM_REF}", "-n", "25",
    )
    print(log.stdout.strip() or "(none)")

    print("\n--- commits on HEAD not in upstream/main (first 25) ---")
    log2 = _git_ok("log", "--oneline", f"{UPSTREAM_REF}..HEAD", "-n", "25")
    print(log2.stdout.strip() or "(none)")

    print("\n--- diff stat vs upstream/main ---")
    ds = _git_ok("diff", "--stat", f"HEAD...{UPSTREAM_REF}")
    print(ds.stdout.strip() or "(no diff)")


def _highlight_watchlist_in_conflicts() -> None:
    p = _git_ok("diff", "--name-only", "--diff-filter=U")
    if p.returncode != 0:
        return
    unmerged = {line.strip() for line in p.stdout.splitlines() if line.strip()}
    if not unmerged:
        return
    watch = {w for w in WATCHLIST_PATHS if w in unmerged}
    print("\n--- unmerged files (watchlist subset) ---")
    if watch:
        for w in sorted(watch):
            print(f"  {w}")
    else:
        print("  (none of the fork watchlist paths are in conflict)")
    print("\n--- all unmerged ---")
    for u in sorted(unmerged):
        print(f"  {u}")


def _run_pytest(targets: tuple[str, ...]) -> int:
    cmd = [sys.executable, "-m", "pytest", "-o", "addopts=", *targets, "-q", "--tb=short"]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT)


def _configure_stdout() -> None:
    """Avoid UnicodeEncodeError when git log contains smart quotes on Windows (cp932)."""
    out = getattr(sys, "stdout", None)
    if out is not None and hasattr(out, "reconfigure"):
        try:
            out.reconfigure(errors="replace")
        except Exception:
            pass


def main() -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(
        description="Sync with NousResearch/hermes-agent (upstream/main).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch upstream and print summary only (no branch, no merge)",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="create sync/upstream-YYYYMMDD from current HEAD and merge upstream/main",
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="after a successful merge, run default tools tests (requires --merge)",
    )
    parser.add_argument(
        "--pytest-only",
        action="store_true",
        help="only run default pytest targets (no git operations)",
    )
    args = parser.parse_args()

    _require_git_repo()

    if args.pytest_only:
        return _run_pytest(DEFAULT_PYTEST_TARGETS)

    if not _upstream_configured():
        print(
            f"error: git remote '{UPSTREAM_REMOTE}' not found.\n"
            f"  git remote add {UPSTREAM_REMOTE} "
            f"https://github.com/NousResearch/hermes-agent.git",
            file=sys.stderr,
        )
        return 2

    print(f"Fetching {UPSTREAM_REMOTE}...")
    fetch = _git_ok("fetch", UPSTREAM_REMOTE)
    if fetch.returncode != 0:
        print(fetch.stderr or fetch.stdout, file=sys.stderr)
        return 1

    _print_summary()

    print("\n--- fork watchlist (review when merging) ---")
    for w in WATCHLIST_PATHS:
        print(f"  {w}")

    if args.dry_run:
        print("\n(dry-run: no branch or merge)")
        return 0

    if not args.merge:
        print("\nPass --merge to create a sync branch and merge, or --dry-run for summary only.")
        return 0

    if not _working_tree_clean():
        print(
            "error: --merge requires a clean working tree (commit or stash first).",
            file=sys.stderr,
        )
        return 2

    day = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    branch = f"sync/upstream-{day}"
    print(f"\nCreating branch {branch} from HEAD...")
    b = _git_ok("branch", "--show-current")
    previous_branch = (b.stdout or "").strip() or "main"

    cb = _git_ok("checkout", "-b", branch)
    if cb.returncode != 0:
        # Branch may exist; try checkout
        cb2 = _git_ok("checkout", branch)
        if cb2.returncode != 0:
            print(cb.stderr or cb.stdout, file=sys.stderr)
            print(cb2.stderr or cb2.stdout, file=sys.stderr)
            return 1

    print(f"Merging {UPSTREAM_REF}...")
    mg = _git_ok("merge", UPSTREAM_REF, "-m", f"Merge {UPSTREAM_REF} into {branch}")
    if mg.returncode != 0:
        print(mg.stderr or mg.stdout, file=sys.stderr)
        _highlight_watchlist_in_conflicts()
        print(
            "\nResolve conflicts, then `git commit` and run:\n"
            f"  py -3 scripts/sync_upstream.py --pytest-only",
            file=sys.stderr,
        )
        return 1

    print(mg.stdout.strip())
    if args.pytest:
        return _run_pytest(DEFAULT_PYTEST_TARGETS)

    print(
        f"\nMerge OK on {branch}. Run tests:\n"
        f"  py -3 scripts/sync_upstream.py --pytest-only\n"
        f"Then merge into {previous_branch} when satisfied: "
        f"git checkout {previous_branch} && git merge {branch}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
