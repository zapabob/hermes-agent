"""Safety regression coverage for the daily VRChat post helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "daily_vrchat_post.py"


def load_daily_post_module():
    spec = importlib.util.spec_from_file_location("daily_vrchat_post_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stop_irodori_server_only_kills_the_configured_process(monkeypatch):
    daily_post = load_daily_post_module()
    calls = []

    monkeypatch.setattr(daily_post, "_listening_port_pids", lambda port: {4321})
    monkeypatch.setattr(
        daily_post,
        "_process_command_line",
        lambda pid: f'"{daily_post.IRODORI_VENV_PYTHON}" -m irodori_openai_tts',
    )
    monkeypatch.setattr(daily_post.time, "sleep", lambda _: None)

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(daily_post.subprocess, "run", fake_run)

    assert daily_post.stop_irodori_server() is True
    assert calls == [["taskkill.exe", "/PID", "4321", "/F"]]


def test_stop_irodori_server_refuses_an_unverified_listener(monkeypatch):
    daily_post = load_daily_post_module()
    calls = []

    monkeypatch.setattr(daily_post, "_listening_port_pids", lambda port: {8765})
    monkeypatch.setattr(daily_post, "_process_command_line", lambda pid: "python unrelated.py")
    monkeypatch.setattr(
        daily_post.subprocess,
        "run",
        lambda *args, **kwargs: calls.append(args) or SimpleNamespace(returncode=0),
    )

    assert daily_post.stop_irodori_server() is False
    assert calls == []


def test_script_does_not_embed_a_specific_windows_username():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "C:\\Users\\downl" not in source
