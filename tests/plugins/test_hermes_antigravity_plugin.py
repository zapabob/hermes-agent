from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any


PLUGIN_DIR = Path(__file__).resolve().parents[2] / "plugins" / "hermes-antigravity"


def load_core() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "hermes_antigravity_core_test", PLUGIN_DIR / "core.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_package() -> ModuleType:
    name = "hermes_antigravity_plugin_test"
    spec = importlib.util.spec_from_file_location(
        name,
        PLUGIN_DIR / "__init__.py",
        submodule_search_locations=[str(PLUGIN_DIR)],
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
        sys.modules.pop(f"{name}.core", None)
    return module


def test_run_uses_empty_workspace_sanitized_env_and_native_permissions(
    monkeypatch, tmp_path: Path
) -> None:
    core = load_core()
    observed: dict[str, Any] = {}

    class TempDir:
        def __init__(self, **_: object) -> None:
            pass

        def __enter__(self) -> str:
            return str(tmp_path)

        def __exit__(self, *_: object) -> None:
            return None

    def fake_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        observed["command"] = command
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="secret-output", stderr="")

    monkeypatch.setattr(core, "find_agy_bin", lambda: str(tmp_path / "agy.exe"))
    monkeypatch.setattr(core.tempfile, "TemporaryDirectory", TempDir)
    monkeypatch.setattr(
        core, "hermes_subprocess_env", lambda *, allowlist_only: {"PATH": "safe"}
    )
    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(
        core, "redact_sensitive_text", lambda text, *, force: f"redacted:{text}"
    )

    result = core.run_agy("hello", model="safe-model", timeout=999)

    assert observed["command"] == [
        str(tmp_path / "agy.exe"),
        "--print",
        "hello",
        "--model",
        "safe-model",
    ]
    assert "--dangerously-skip-permissions" not in observed["command"]
    assert observed["cwd"] == str(tmp_path)
    assert observed["env"] == {"PATH": "safe"}
    assert observed["stdin"] is subprocess.DEVNULL
    assert observed["timeout"] == 600
    assert result["agy_bin"] == "agy.exe"
    assert result["stdout"] == "redacted:secret-output"


def test_tool_schema_rejects_hidden_extra_arguments_and_gates_execution(
    monkeypatch,
) -> None:
    plugin = load_package()
    registered: list[dict[str, Any]] = []

    class Context:
        def register_tool(self, **kwargs: Any) -> None:
            registered.append(kwargs)

    monkeypatch.setattr(plugin, "find_agy_bin", lambda: None)
    plugin.register(Context())

    tools = {item["name"]: item for item in registered}
    run_tool = tools["antigravity_run"]
    assert run_tool["schema"]["additionalProperties"] is False
    assert "extra_args" not in run_tool["schema"]["properties"]
    assert "dangerously_skip_permissions" not in run_tool["schema"]["properties"]
    assert run_tool["check_fn"]() is False
    assert tools["antigravity_status"]["check_fn"]() is True


def test_candidate_paths_do_not_embed_a_developer_profile() -> None:
    source = (PLUGIN_DIR / "core.py").read_text(encoding="utf-8")

    assert r"C:\Users\downl\AppData\Local\agy" not in source


def test_windows_candidate_rejects_shell_wrappers(
    monkeypatch, tmp_path: Path
) -> None:
    host_os_name = os.name
    core = load_core()
    cmd = tmp_path / "agy.cmd"
    exe = tmp_path / "agy.exe"
    cmd.write_text("@echo off\n", encoding="utf-8")
    exe.write_bytes(b"MZ")
    real_os = core.os
    monkeypatch.setattr(
        core,
        "os",
        SimpleNamespace(
            name="nt",
            path=real_os.path,
            access=real_os.access,
            X_OK=real_os.X_OK,
        ),
    )
    assert os.name == host_os_name

    assert core._is_executable_candidate(str(cmd)) is False
    assert core._is_executable_candidate(str(exe)) is True
