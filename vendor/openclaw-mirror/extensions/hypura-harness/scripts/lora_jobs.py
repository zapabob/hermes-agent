"""Persistent-ish job store for LoRA / curriculum async jobs (JSON files)."""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

JobStatus = Literal["pending", "running", "completed", "failed"]


@dataclass
class JobRecord:
    job_id: str
    kind: str
    status: JobStatus
    created_at: float
    updated_at: float
    message: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class JobStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, job_id: str) -> Path:
        return self._root / f"{job_id}.json"

    def create(self, kind: str) -> JobRecord:
        job_id = str(uuid.uuid4())
        now = time.time()
        rec = JobRecord(
            job_id=job_id,
            kind=kind,
            status="pending",
            created_at=now,
            updated_at=now,
        )
        self._write(rec)
        return rec

    def get(self, job_id: str) -> JobRecord | None:
        p = self._path(job_id)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return JobRecord(
            job_id=data["job_id"],
            kind=data.get("kind", "unknown"),
            status=data.get("status", "pending"),
            created_at=float(data.get("created_at", 0)),
            updated_at=float(data.get("updated_at", 0)),
            message=data.get("message", ""),
            result=data.get("result") or {},
            error=data.get("error"),
        )

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        message: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> JobRecord | None:
        with self._lock:
            rec = self.get(job_id)
            if rec is None:
                return None
            if status is not None:
                rec.status = status
            if message is not None:
                rec.message = message
            if result is not None:
                rec.result = result
            if error is not None:
                rec.error = error
            rec.updated_at = time.time()
            self._write(rec)
            return rec

    def _write(self, rec: JobRecord) -> None:
        p = self._path(rec.job_id)
        p.write_text(json.dumps(asdict(rec), indent=2), encoding="utf-8")
