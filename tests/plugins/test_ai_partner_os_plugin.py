from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parents[2] / "plugins" / "ai-partner-os"


def load_core():
    package_name = "ai_partner_os_test_plugin"
    for name in list(sys.modules):
        if name == package_name or name.startswith(f"{package_name}."):
            del sys.modules[name]

    package = types.ModuleType(package_name)
    package.__path__ = [str(PLUGIN_DIR)]  # type: ignore[attr-defined]
    sys.modules[package_name] = package

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.core",
        PLUGIN_DIR / "core.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package_name
    sys.modules[f"{package_name}.core"] = module
    spec.loader.exec_module(module)
    return module


def load_process():
    package_name = "ai_partner_os_test_process"
    for name in list(sys.modules):
        if name == package_name or name.startswith(f"{package_name}."):
            del sys.modules[name]

    package = types.ModuleType(package_name)
    package.__path__ = [str(PLUGIN_DIR)]
    sys.modules[package_name] = package

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.process",
        PLUGIN_DIR / "process.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = package_name
    sys.modules[f"{package_name}.process"] = module
    spec.loader.exec_module(module)
    return module


def test_bridge_start_rejects_public_host_without_confirmation():
    core = load_core()

    payload = core.start_bridge({"host": "0.0.0.0"})

    assert payload["ok"] is False
    assert payload["confirmation_required"] is True
    assert "noauth WebSocket" in payload["reason"]


def test_bridge_start_rejects_tailscale_bind_without_confirmation():
    core = load_core()

    payload = core.start_bridge({"tailscale": True})

    assert payload["ok"] is False
    assert payload["confirmation_required"] is True
    assert payload["host"] == "0.0.0.0"


def test_start_exe_closes_descriptors_and_uses_strict_environment(monkeypatch, tmp_path):
    process = load_process()
    exe = tmp_path / "partner.exe"
    exe.write_bytes(b"test")
    monkeypatch.setattr(process, "read_state", lambda: {})
    monkeypatch.setattr(process, "pid_alive", lambda pid: False)
    monkeypatch.setattr(process, "write_state", lambda payload: None)
    for key, value in {
        "HERMES_TEST_SECRET_CANARY": "HERMES_CANARY_DO_NOT_LEAK_8F421",
        "OPENAI_API_KEY": "sk-test-HERMES-CANARY",
        "GITHUB_TOKEN": "ghp_test_canary",
        "MY_APP_VAR": "must-not-be-inherited",
    }.items():
        monkeypatch.setenv(key, value)

    captured = {}

    class FakeProc:
        pid = 4242

    def fake_popen(cmd, **kwargs):
        captured.update(kwargs)
        return FakeProc()

    monkeypatch.setattr(process.subprocess, "Popen", fake_popen)

    result = process.start_exe(exe)

    assert result["ok"] is True
    assert captured["close_fds"] is True
    assert isinstance(captured["env"], dict)
    assert "PATH" in captured["env"]
    for key in (
        "HERMES_TEST_SECRET_CANARY",
        "OPENAI_API_KEY",
        "GITHUB_TOKEN",
        "MY_APP_VAR",
    ):
        assert key not in captured["env"]
