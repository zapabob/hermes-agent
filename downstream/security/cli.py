from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any, Protocol

import psutil

from hermes_cli._subprocess_compat import windows_detach_flags, windows_hide_flags
from tools.environments.local import hermes_subprocess_env

from .service import SecurityService


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


class _WatchService(Protocol):
    config: dict[str, Any]
    store: _WatchStore

    def watch_status(self) -> dict[str, object]: ...


def _emit(value: Any, machine: bool) -> None:
    if machine:
        sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
        return
    if isinstance(value, list):
        for item in value:
            sys.stdout.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            sys.stdout.write(f"{key}: {json.dumps(item, ensure_ascii=False, default=str)}\n")
        return
    sys.stdout.write(f"{value}\n")


def _watch_enable(service: _WatchService) -> dict[str, Any]:
    current = service.watch_status()
    if current.get("running"):
        return {"ok": True, **current}
    flags = windows_detach_flags() | windows_hide_flags()
    interval = max(2.0, float(service.config.get("watch_interval", 30)))
    process = subprocess.Popen(
        [sys.executable, "-m", "downstream.security.watcher", "--interval", str(interval)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=hermes_subprocess_env(inherit_credentials=False),
        creationflags=flags,
        start_new_session=sys.platform != "win32",
    )
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        state = service.watch_status()
        if state.get("running"):
            service.store.event("watch", str(state.get("pid")), None, "enabled", {})
            return {"ok": True, **state}
        time.sleep(0.05)
    return {"ok": False, "enabled": False, "pid": process.pid, "running": False, "error": "watcher did not report ready within 5 seconds"}


def _watch_disable(service: _WatchService) -> dict[str, Any]:
    current = service.watch_status()
    raw_pid = current.get("pid")
    pid = raw_pid if isinstance(raw_pid, int) else 0
    if pid and psutil.pid_exists(pid):
        process = psutil.Process(pid)
        process.terminate()
        try:
            process.wait(timeout=10)
        except psutil.TimeoutExpired:
            return {"ok": False, "error": "watcher did not stop within 10 seconds", **current}
    state_path = service.store.root / "watch-state.json"
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"enabled": False, "pid": None}, sort_keys=True), encoding="utf-8")
    os.replace(temporary, state_path)
    service.store.event("watch", str(pid or "none"), None, "disabled", {})
    return {"ok": True, "enabled": False, "pid": None, "running": False}


def command(args: Namespace) -> int:
    service = SecurityService()
    subcommand = args.security_command
    machine = bool(getattr(args, "json", False))
    try:
        if subcommand == "status":
            result = service.status()
        elif subcommand == "scan":
            paths = service.quick_paths() if args.quick else service.full_paths() if args.full else [Path(args.path)]
            result = [item.to_dict() for item in service.scan_paths(paths, quarantine=not args.no_quarantine)]
        elif subcommand == "update":
            result = service.update()
        elif subcommand == "feeds":
            result = service.store.status_rows("feed_state", 200)
        elif subcommand == "watch":
            result = service.watch_status() if args.watch_command == "status" else _watch_enable(service) if args.watch_command == "enable" else _watch_disable(service)
        elif subcommand == "quarantine":
            if args.quarantine_command == "list":
                result = service.store.status_rows("quarantine_items", 200)
            elif args.quarantine_command == "inspect":
                result = service.vault.inspect(args.item_id)
            elif args.quarantine_command == "restore":
                target = Path(args.destination).resolve() if args.destination else None
                restored = service.vault.restore(args.item_id, lambda path: service.scan_file(path, quarantine=False, use_cache=False), target, args.force)
                result = {"ok": True, "path": str(restored)}
            else:
                service.vault.delete(args.item_id)
                result = {"ok": True, "id": args.item_id, "deleted": True}
        else:
            raise ValueError(f"unknown security subcommand: {subcommand}")
    except (FileNotFoundError, KeyError, PermissionError, RuntimeError, ValueError) as exc:
        _emit({"ok": False, "error": str(exc)}, machine)
        return 2
    _emit(result, machine)
    if isinstance(result, dict) and result.get("ok") is False:
        return 1
    return 0
