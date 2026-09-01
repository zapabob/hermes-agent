"""Lease-backed coordination with the external Windows watchdog.

The Go watchdog is the outer recovery authority.  During a planned update the
updater owns process shutdown and recovery, so this module publishes a small,
atomic state record that makes the watchdog observational until recovery is
complete.  The lease prevents a crashed updater from disabling supervision
forever.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Mapping

from hermes_constants import get_hermes_home

NORMAL = "NORMAL"
UPDATE_PREPARE = "UPDATE_PREPARE"
UPSTREAM_DRAIN = "UPSTREAM_DRAIN"
UPDATE = "UPDATE"
RECOVERY = "RECOVERY"

_VALID_STATES = frozenset(
    {NORMAL, UPDATE_PREPARE, UPSTREAM_DRAIN, UPDATE, RECOVERY}
)
DEFAULT_LEASE_SECONDS = 4 * 60 * 60


@dataclass(frozen=True)
class WatchdogMaintenanceLease:
    path: Path
    owner: str
    nonce: str
    epoch: int
    reason: str
    lease_seconds: int
    repo_root: str
    handoff_parent: bool = False


def maintenance_path(
    env: Mapping[str, str] | None = None,
    *,
    hermes_home: Path | None = None,
) -> Path:
    """Return the state path shared with ``hermes-watchdog``."""
    values = os.environ if env is None else env
    explicit = str(values.get("HERMES_WATCHDOG_DATA", "")).strip()
    if explicit:
        data_dir = Path(explicit)
    elif values.get("PYTEST_CURRENT_TEST"):
        # Parallel test workers must never coordinate through the operator's
        # live %LOCALAPPDATA% watchdog state.
        data_dir = (hermes_home or get_hermes_home()) / "watchdog-go"
    else:
        local = str(values.get("LOCALAPPDATA", "")).strip()
        data_dir = (
            Path(local) / "HermesWatchdog"
            if local
            else (hermes_home or get_hermes_home()) / "watchdog-go"
        )
    return data_dir / "maintenance.json"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        value = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _read_state(path: Path) -> dict[str, object] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(raw, dict):
        raise RuntimeError(f"Invalid watchdog maintenance state: {path}")
    return raw


def _state_is_live(payload: Mapping[str, object], now: datetime) -> bool:
    if payload.get("state") == NORMAL:
        return False
    expires_at = _parse_timestamp(payload.get("leaseExpiresAt"))
    return expires_at is not None and expires_at > now


def _process_start_time(pid: int) -> float | None:
    try:
        import psutil

        return float(psutil.Process(pid).create_time())
    except Exception:
        return None


def _owner_is_alive(payload: Mapping[str, object]) -> bool:
    try:
        pid = int(payload.get("pid") or 0)
    except (TypeError, ValueError):
        return True
    if pid <= 0:
        return True
    current_start = _process_start_time(pid)
    if current_start is None:
        return False
    recorded_start = payload.get("processStartTime")
    if recorded_start is None:
        return True
    try:
        return abs(current_start - float(recorded_start)) <= 0.001
    except (TypeError, ValueError):
        return True


def _atomic_write(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with tmp.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _payload(
    lease: WatchdogMaintenanceLease,
    state: str,
    *,
    reason: str,
    now: datetime,
) -> dict[str, object]:
    expires_at = now if state == NORMAL else now + timedelta(seconds=lease.lease_seconds)
    return {
        "schemaVersion": 1,
        "state": state,
        "owner": lease.owner,
        "nonce": lease.nonce,
        "epoch": lease.epoch,
        "timestamp": _format_timestamp(now),
        "reason": reason,
        "leaseSeconds": lease.lease_seconds,
        "leaseExpiresAt": _format_timestamp(expires_at),
        "pid": os.getpid(),
        "processStartTime": _process_start_time(os.getpid()),
        "repoRoot": lease.repo_root,
    }


def acquire(
    repo_root: Path,
    *,
    reason: str = "Hermes update",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    path: Path | None = None,
    now: datetime | None = None,
) -> WatchdogMaintenanceLease:
    """Acquire the planned-maintenance lease or fail on a live owner."""
    if lease_seconds <= 0:
        raise ValueError("lease_seconds must be positive")
    state_path = path or maintenance_path()
    current_time = now or _utc_now()
    existing = _read_state(state_path)
    if existing is not None and _state_is_live(existing, current_time):
        inherited_owner = os.environ.get(
            "HERMES_WATCHDOG_MAINTENANCE_OWNER", ""
        ).strip()
        inherited_nonce = os.environ.get(
            "HERMES_WATCHDOG_MAINTENANCE_NONCE", ""
        ).strip()
        inherited_epoch = os.environ.get(
            "HERMES_WATCHDOG_MAINTENANCE_EPOCH", ""
        ).strip()
        if (
            inherited_owner
            and inherited_nonce
            and existing.get("owner") == inherited_owner
            and existing.get("nonce") == inherited_nonce
            and str(existing.get("epoch")) == inherited_epoch
        ):
            return WatchdogMaintenanceLease(
                path=state_path,
                owner=inherited_owner,
                nonce=inherited_nonce,
                epoch=int(inherited_epoch),
                reason=str(existing.get("reason") or reason),
                lease_seconds=int(existing.get("leaseSeconds") or lease_seconds),
                repo_root=str(existing.get("repoRoot") or Path(repo_root).resolve()),
                handoff_parent=True,
            )
        if _owner_is_alive(existing):
            owner = existing.get("owner") or "unknown"
            raise RuntimeError(
                f"Watchdog maintenance is already owned by {owner}; update refused"
            )

    lease = WatchdogMaintenanceLease(
        path=state_path,
        owner=f"hermes-update:{os.getpid()}",
        nonce=uuid.uuid4().hex,
        epoch=time.time_ns(),
        reason=reason,
        lease_seconds=int(lease_seconds),
        repo_root=str(Path(repo_root).resolve()),
    )
    _atomic_write(
        state_path,
        _payload(lease, UPDATE_PREPARE, reason=reason, now=current_time),
    )
    return lease


def transition(
    lease: WatchdogMaintenanceLease,
    state: str,
    *,
    reason: str | None = None,
    now: datetime | None = None,
) -> None:
    """Advance a lease-owned state after verifying owner and nonce."""
    if state not in _VALID_STATES:
        raise ValueError(f"Unsupported watchdog maintenance state: {state}")
    existing = _read_state(lease.path)
    if existing is None:
        raise RuntimeError("Watchdog maintenance state disappeared")
    if existing.get("owner") != lease.owner or existing.get("nonce") != lease.nonce:
        raise RuntimeError("Watchdog maintenance ownership changed")
    _atomic_write(
        lease.path,
        _payload(
            lease,
            state,
            reason=reason or lease.reason,
            now=now or _utc_now(),
        ),
    )


def release(
    lease: WatchdogMaintenanceLease,
    *,
    reason: str = "Hermes update recovery complete",
) -> None:
    if lease.handoff_parent:
        transition(
            lease,
            RECOVERY,
            reason="Desktop update handoff retains recovery ownership",
        )
        return
    transition(lease, NORMAL, reason=reason)
