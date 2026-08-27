from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path
from typing import Any, Protocol

import psutil

from .service import SecurityService, is_reparse_point


class _WatchStore(Protocol):
    root: Path

    def event(
        self,
        event_type: str,
        subject: str,
        verdict: str | None,
        action: str,
        details: dict[str, Any],
    ) -> None: ...


class _ReconcileService(Protocol):
    store: _WatchStore

    def quick_paths(self) -> list[Path]: ...

    def scan_file(self, candidate: Path | str, quarantine: bool = True, use_cache: bool = True) -> object: ...


def _write_state(service: SecurityService, enabled: bool) -> None:
    path = service.store.root / "watch-state.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"enabled": enabled, "pid": os.getpid()}, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def reconcile_once(
    service: _ReconcileService,
    seen: dict[str, tuple[int, int]],
    *,
    scan_changes: bool = True,
) -> dict[str, tuple[int, int]]:
    current: dict[str, tuple[int, int]] = {}
    for root in service.quick_paths():
        for directory, dirnames, names in os.walk(root, followlinks=False):
            dirnames[:] = [name for name in dirnames if not is_reparse_point(Path(directory) / name)]
            for name in names:
                path = Path(directory) / name
                if is_reparse_point(path):
                    continue
                try:
                    stat_result = path.stat()
                except OSError:
                    continue
                identity = (stat_result.st_size, stat_result.st_mtime_ns)
                key = str(path)
                current[key] = identity
                if scan_changes and seen.get(key) != identity:
                    try:
                        service.scan_file(path)
                    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
                        service.store.event("watch_scan_error", key, None, "scan_failed", {"error": str(exc)})
    return current


def run(interval: float) -> int:
    service = SecurityService()
    stopping = False
    if os.name == "nt":
        try:
            psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        except (OSError, psutil.Error):
            pass

    def request_stop(_signum, _frame) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, request_stop)
    seen = reconcile_once(service, {}, scan_changes=False)
    _write_state(service, True)
    try:
        while not stopping:
            seen = reconcile_once(service, seen)
            deadline = time.monotonic() + max(2.0, interval)
            while not stopping and time.monotonic() < deadline:
                time.sleep(min(0.5, deadline - time.monotonic()))
    finally:
        _write_state(service, False)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=30.0)
    args = parser.parse_args()
    return run(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
