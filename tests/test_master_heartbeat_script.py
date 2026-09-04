from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "master-heartbeat.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("master_heartbeat", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_args_defaults_to_serial_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH)])

    args = module.parse_args()

    assert args.smoke is True
    assert args.timeout == 120
    assert args.concurrency == 1


def test_import_does_not_promote_default_profile_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    default_env = tmp_path / ".hermes" / ".env"
    default_env.parent.mkdir(parents=True)
    default_env.write_text("NVIDIA_API_KEY=default-profile-canary\n", encoding="utf-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    load_module()

    assert "NVIDIA_API_KEY" not in os.environ


def test_classify_output_marks_capacity_failures() -> None:
    module = load_module()

    ok, reason = module.classify_output(
        1,
        "API call failed after 3 retries: HTTP 429: Too Many Requests",
        "",
    )

    assert ok is False
    assert reason in {"HTTP 429", "API call failed after 3 retries"}


def test_main_returns_failure_when_any_profile_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_module()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "--profiles", "job-seeker"])
    monkeypatch.setattr(module, "HERMES_CMD", str(SCRIPT_PATH))
    monkeypatch.setattr(module, "A2A_RESULTS_DIR", tmp_path)

    async def fake_run_all(*_: object, **__: object) -> list[dict[str, object]]:
        return [{"ok": False, "profile": "job-seeker", "task": "PONG", "error": "timeout"}]

    monkeypatch.setattr(module, "run_all", fake_run_all)

    assert asyncio.run(module.main()) == 1
