#!/usr/bin/env python3
"""Synchronize reviewed operational scripts from a repository to Hermes home.

The repository is authoritative.  Synchronization is deliberately limited to
the reviewed allowlist below and is dry-run by default.  It never copies
configuration, databases, logs, credentials, models, or arbitrary files from
``HERMES_HOME`` into the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable


# Operational cron scripts only.  Add a script only after a source and privacy
# review; arbitrary files under ~/.hermes/scripts are intentionally untouched.
ALLOWLIST = (
    "cross-platform-memory-sleep-fallback.py",
    "daily_moa_provider_selector.py",
    "daily_vrchat_post.py",
    "disaster-news-jp.py",
    "lm-twitterer-post.py",
    "lm-twitterer-replies.py",
    "lm-twitterer-topic-bank-post.py",
    "lm-twitterer-topic-bank-weekly-update.py",
    "mhlw-designated-check.py",
    "osint-agent-evening.py",
    "osint-agent-morning.py",
    "warashibe-hourly-arb-scan.py",
    "warashibe-x-niche-price-scan.py",
    "wm-osint-pdb-evening.py",
    "wm-osint-pdb-morning.py",
    "worldmonitor-fusion-jp-security-noagent.py",
)


@dataclass(frozen=True)
class SyncResult:
    mode: str
    allowlist_count: int
    imported_to_repo: list[str]
    deployed_to_hermes: list[str]
    unchanged: list[str]
    drift: list[str]
    missing_repo: list[str]
    missing_hermes: list[str]
    errors: list[str]
    report_written: bool = False

    @property
    def is_clean(self) -> bool:
        return not (
            self.drift
            or self.missing_repo
            or self.missing_hermes
            or self.errors
        )


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _validated_name(name: str) -> PurePosixPath:
    candidate = PurePosixPath(name)
    if candidate.is_absolute() or ".." in candidate.parts or len(candidate.parts) != 1:
        raise ValueError(f"allowlist entry is not a single relative filename: {name!r}")
    return candidate


def _safe_child(root: Path, name: str) -> Path:
    child = root / _validated_name(name)
    if not _is_within(child, root):
        raise ValueError(f"refusing path outside sync root: {name!r}")
    return child


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _copy_atomically(source: Path, destination: Path) -> None:
    if not _regular_file(source):
        raise ValueError(f"source is not a regular file: {source.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.is_symlink():
        raise ValueError(f"destination is a symlink: {destination.name}")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as target, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, target, length=1024 * 1024)
        shutil.copystat(source, temporary)
        if digest(source) != digest(temporary):
            raise RuntimeError(f"checksum mismatch while preparing {destination.name}")
        os.replace(temporary, destination)
        if digest(source) != digest(destination):
            raise RuntimeError(f"checksum mismatch after deploying {destination.name}")
    finally:
        temporary.unlink(missing_ok=True)


def _build_result(mode: str) -> SyncResult:
    return SyncResult(
        mode=mode,
        allowlist_count=len(ALLOWLIST),
        imported_to_repo=[],
        deployed_to_hermes=[],
        unchanged=[],
        drift=[],
        missing_repo=[],
        missing_hermes=[],
        errors=[],
    )


def synchronize(
    *,
    repo_root: Path,
    hermes_home: Path,
    apply: bool,
    check: bool,
    bootstrap_from_hermes: bool,
) -> SyncResult:
    mode = "check" if check else "apply" if apply else "dry-run"
    result = _build_result(mode)
    repo_scripts = repo_root / "scripts"
    hermes_scripts = hermes_home / "scripts"

    if not repo_scripts.is_dir():
        result.errors.append("repository scripts directory is missing")
        return result

    for name in ALLOWLIST:
        try:
            repo_path = _safe_child(repo_scripts, name)
            hermes_path = _safe_child(hermes_scripts, name)
        except ValueError as exc:
            result.errors.append(str(exc))
            continue

        repo_exists = _regular_file(repo_path)
        hermes_exists = _regular_file(hermes_path)

        if not repo_exists:
            if bootstrap_from_hermes and hermes_exists:
                if apply:
                    _copy_atomically(hermes_path, repo_path)
                    result.imported_to_repo.append(name)
                    repo_exists = True
                else:
                    result.drift.append(name)
                    continue
            else:
                result.missing_repo.append(name)
                continue

        if not hermes_exists:
            if apply:
                _copy_atomically(repo_path, hermes_path)
                result.deployed_to_hermes.append(name)
            else:
                result.missing_hermes.append(name)
            continue

        if digest(repo_path) == digest(hermes_path):
            result.unchanged.append(name)
            continue

        result.drift.append(name)
        if apply:
            _copy_atomically(repo_path, hermes_path)
            result.deployed_to_hermes.append(name)

    return result


def _write_report(result: SyncResult, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        **asdict(result),
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{report_path.name}.", suffix=".tmp", dir=report_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, report_path)
    finally:
        temporary.unlink(missing_ok=True)


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Hermes repository root (default: this script's repository).",
    )
    parser.add_argument(
        "--hermes-home",
        type=Path,
        default=Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")),
        help="Target Hermes home (default: HERMES_HOME or ~/.hermes).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy reviewed repository scripts to Hermes home and write a report.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when an allowlisted repository/home script is missing or differs.",
    )
    parser.add_argument(
        "--bootstrap-from-hermes",
        action="store_true",
        help="With --apply only, import a missing allowlisted repository file from Hermes home.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Override the apply-only JSON report location.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the reviewed allowlist as JSON and exit.",
    )
    args = parser.parse_args(list(argv))
    if args.apply and args.check:
        parser.error("--apply and --check are mutually exclusive")
    if args.bootstrap_from_hermes and not args.apply:
        parser.error("--bootstrap-from-hermes requires --apply")
    if args.report and not args.apply:
        parser.error("--report requires --apply")
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.list:
        print(json.dumps({"allowlist": ALLOWLIST}, ensure_ascii=False))
        return 0

    result = synchronize(
        repo_root=args.repo_root,
        hermes_home=args.hermes_home,
        apply=args.apply,
        check=args.check,
        bootstrap_from_hermes=args.bootstrap_from_hermes,
    )

    if args.apply:
        report_path = args.report or args.hermes_home / "sync-reports" / "latest-operational-script-sync.json"
        result = SyncResult(**{**asdict(result), "report_written": True})
        _write_report(result, report_path)

    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    if args.check:
        return 0 if result.is_clean else 1
    if args.apply:
        return 0 if not result.missing_repo and not result.errors else 1
    return 0 if not result.missing_repo and not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
