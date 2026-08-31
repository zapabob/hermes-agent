from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock


PLUGIN_DIR = Path(__file__).resolve().parents[2] / "plugins" / "sillytavern"


def load_plugin():
    package_name = "sillytavern_test_plugin"
    for name in list(sys.modules):
        if name == package_name or name.startswith(f"{package_name}."):
            del sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        package_name,
        PLUGIN_DIR / "__init__.py",
        submodule_search_locations=[str(PLUGIN_DIR)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module
    spec.loader.exec_module(module)
    return module


class _Context:
    def __init__(self):
        self.tools = []
        self.commands = []
        self.cli_commands = {}

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_command(self, *args, **kwargs):
        self.commands.append((args, kwargs))

    def register_cli_command(self, name, **kwargs):
        self.cli_commands[name] = kwargs


def test_register_exposes_sillytavern_to_agents():
    module = load_plugin()
    context = _Context()
    module.register(context)

    assert {tool["name"] for tool in context.tools} == {
        "sillytavern_status",
        "sillytavern_start",
        "sillytavern_stop",
        "sillytavern_version",
        "sillytavern_configure",
        "sillytavern_scan",
        "sillytavern_import_memory",
        "sillytavern_proxy_start",
        "sillytavern_proxy_stop",
        "sillytavern_proxy_status",
        "st_audio_land",
        "st_character_create",
        "st_character_list",
        "st_lore_add",
        "st_memory_to_lore",
        "st_persona_create",
        "st_session_reply",
        "st_session_say",
        "st_session_start",
        "st_session_summary",
        "st_session_to_memory",
        "st_voice_roleplay",
        "st_voice_roleplay_complete",
    }
    assert all(callable(tool["handler"]) for tool in context.tools)
    assert all(
        tool.get("check_fn") is None or callable(tool["check_fn"])
        for tool in context.tools
    )
    slash_names = {args[0] for args, _ in context.commands}
    assert slash_names == {"rp", "st-voice-roleplay"}
    assert "sillytavern" in context.cli_commands
    assert callable(context.cli_commands["sillytavern"]["setup_fn"])
    assert callable(context.cli_commands["sillytavern"]["handler_fn"])


def test_status_reports_install_state(monkeypatch, tmp_path):
    module = load_plugin()
    monkeypatch.setattr(module, "_get_dir", lambda: str(tmp_path))
    monkeypatch.setattr(module, "_is_up", lambda timeout=3.0: False)
    payload = json.loads(module.sillytavern_status({}, task_id=None))
    assert payload["installed"] is False
    assert payload["running"] is False
    assert payload["install_dir"] == str(tmp_path)


def test_configure_returns_structured_result(monkeypatch):
    module = load_plugin()
    monkeypatch.setattr(
        module,
        "_configure",
        lambda: {"written_secrets": ["openai_api_key"], "local_llama": True},
    )
    payload = json.loads(module.sillytavern_configure({}, task_id=None))
    assert payload["ok"] is True
    assert payload["written_secrets"] == ["openai_api_key"]
    assert payload["local_llama"] is True


def test_start_uses_managed_node_and_strict_environment(monkeypatch, tmp_path):
    module = load_plugin()
    module._STATE.clear()
    states = iter((False, True))
    monkeypatch.setattr(module, "_installed", lambda: True)
    monkeypatch.setattr(module, "_is_up", lambda: next(states))
    monkeypatch.setattr(module, "_get_dir", lambda: str(tmp_path))
    monkeypatch.setattr(
        module,
        "_configure",
        lambda: {"secrets_written": [], "settings_changed": []},
    )
    monkeypatch.setattr(
        module,
        "find_node_executable",
        lambda command: "C:/Hermes/node.exe",
        raising=False,
    )
    for key, value in {
        "HERMES_TEST_SECRET_CANARY": "HERMES_CANARY_DO_NOT_LEAK_8F421",
        "OPENAI_API_KEY": "sk-test-HERMES-CANARY",
        "ANTHROPIC_API_KEY": "test-anthropic-canary",
        "GITHUB_TOKEN": "ghp_test_canary",
        "HF_TOKEN": "hf_test_canary",
        "MY_APP_VAR": "must-not-be-inherited",
    }.items():
        monkeypatch.setenv(key, value)

    captured = {}

    class FakeProc:
        pid = 4242

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env")
        return FakeProc()

    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    payload = json.loads(module.sillytavern_start({}, task_id=None))

    assert payload["ok"] is True
    assert captured["cmd"][0] == "C:/Hermes/node.exe"
    assert isinstance(captured["env"], dict)
    assert "PATH" in captured["env"]
    for key in (
        "HERMES_TEST_SECRET_CANARY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
        "HF_TOKEN",
        "MY_APP_VAR",
    ):
        assert key not in captured["env"]


def test_stop_taskkill_sets_stdin(monkeypatch):
    module = load_plugin()
    module._STATE.clear()
    monkeypatch.setattr(
        module.subprocess,
        "check_output",
        lambda *args, **kwargs: (
            "  TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    4242\n"
        ),
    )
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["stdin"] = kwargs.get("stdin")
        return MagicMock(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    payload = json.loads(module.sillytavern_stop({}, task_id=None))
    assert payload["ok"] is True
    assert "4242" in payload["killed_pids"]
    assert captured["cmd"] == ["taskkill", "/PID", "4242", "/F"]
    assert captured["stdin"] is subprocess.DEVNULL
