from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from .models import EngineState
from .store import SecurityStore


class DefinitionUpdater:
    def __init__(self, store: SecurityStore, timeout: int = 300) -> None:
        self.store = store
        self.timeout = max(30, timeout)
        self.root = store.root / "feeds" / "clamav"
        self.root.mkdir(parents=True, exist_ok=True)

    def _validate(self, candidate: Path) -> tuple[bool, str]:
        databases = sorted(candidate.glob("*.cvd")) + sorted(candidate.glob("*.cld"))
        if not databases or any(path.stat().st_size < 512 for path in databases):
            return False, "freshclam produced no valid CVD/CLD database"
        sigtool = shutil.which("sigtool")
        if sigtool:
            for database in databases:
                result = subprocess.run(
                    [sigtool, "--info", str(database)], capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=30, check=False,
                    stdin=subprocess.DEVNULL,
                )
                if result.returncode != 0:
                    return False, f"sigtool rejected {database.name}"
        return True, f"{len(databases)} databases validated"

    def _activate(self, staging: Path) -> None:
        current = self.root / "current"
        previous = self.root / "previous"
        discard = self.root / f".previous-{uuid.uuid4().hex}"
        moved_current = False
        if previous.exists():
            os.replace(previous, discard)
        try:
            if current.exists():
                os.replace(current, previous)
                moved_current = True
            os.replace(staging, current)
        except Exception:
            if moved_current and previous.exists() and not current.exists():
                os.replace(previous, current)
            if discard.exists() and not previous.exists():
                os.replace(discard, previous)
            raise
        if discard.exists():
            shutil.rmtree(discard)

    def update_clamav(self) -> dict[str, Any]:
        freshclam = shutil.which("freshclam")
        if not freshclam:
            self.store.upsert_feed("clamav", EngineState.SCANNER_UNAVAILABLE.value, "error", {"error": "freshclam unavailable"})
            return {"ok": False, "state": EngineState.SCANNER_UNAVAILABLE.value, "error": "freshclam unavailable"}
        staging = self.root / f".staging-{uuid.uuid4().hex}"
        staging.mkdir()
        try:
            result = subprocess.run(
                [freshclam, f"--datadir={staging}"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=self.timeout, check=False,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            shutil.rmtree(staging, ignore_errors=True)
            self.store.upsert_feed("clamav", EngineState.SCAN_TIMEOUT.value, "error", {"error": "freshclam timeout"})
            return {"ok": False, "state": EngineState.SCAN_TIMEOUT.value, "error": "freshclam timeout"}
        output = "\n".join((result.stdout, result.stderr)).strip()[-2000:]
        if result.returncode != 0:
            shutil.rmtree(staging, ignore_errors=True)
            self.store.upsert_feed("clamav", "update_failed", "error", {"exit_code": result.returncode, "output": output})
            return {"ok": False, "state": "update_failed", "error": output, "exit_code": result.returncode}
        valid, validation = self._validate(staging)
        if not valid:
            shutil.rmtree(staging, ignore_errors=True)
            self.store.upsert_feed("clamav", "validation_failed", "error", {"error": validation})
            return {"ok": False, "state": "validation_failed", "error": validation}
        try:
            self._activate(staging)
        except OSError as exc:
            shutil.rmtree(staging, ignore_errors=True)
            self.store.upsert_feed("clamav", "activation_failed", "error", {"error": str(exc)})
            return {"ok": False, "state": "activation_failed", "error": str(exc)}
        current = self.root / "current"
        version = str(max((path.stat().st_mtime_ns for path in current.iterdir()), default=0))
        self.store.upsert_feed("clamav", version, "ok", {"validation": validation})
        return {"ok": True, "state": "ok", "version": version, "validation": validation}
