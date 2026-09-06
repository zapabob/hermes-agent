"""Runtime contracts for Hermes' pinned agent-browser execution boundary."""

from __future__ import annotations

from types import SimpleNamespace

import tools.browser_tool as bt


def test_browser_child_env_forces_webmcp_off(monkeypatch):
    """An ambient opt-in must not widen an agent-browser child capability."""
    from tools.environments import local

    monkeypatch.setenv("AGENT_BROWSER_NO_WEBMCP", "0")
    monkeypatch.setattr(
        local,
        "hermes_subprocess_env",
        lambda *, inherit_credentials: {"PATH": "C:\\safe"},
    )

    env = bt._build_browser_env()

    assert env["AGENT_BROWSER_NO_WEBMCP"] == "1"


def test_npx_resolution_does_not_probe_node_during_readiness(monkeypatch):
    """The resolver remains a no-child-process readiness operation."""
    monkeypatch.setattr(
        bt, "_agent_browser_node_is_compatible",
        lambda: (_ for _ in ()).throw(AssertionError("readiness must not probe Node")),
    )
    monkeypatch.setattr(bt, "_merge_browser_path", lambda _path: "")
    monkeypatch.setattr(bt.shutil, "which", lambda *_args, **_kwargs: "npx")
    monkeypatch.setattr(bt, "node_tool_runnable", lambda _path: True)

    assert bt._resolve_npx_bin() == "npx"


def test_npx_resolution_allows_node_24_or_newer(monkeypatch):
    monkeypatch.setattr(bt, "_merge_browser_path", lambda _path: "C:\\hermes\\node")
    monkeypatch.setattr(
        bt.shutil,
        "which",
        lambda command, path=None: "C:\\hermes\\node\\npx.cmd"
        if command == "npx"
        else None,
    )
    monkeypatch.setattr(bt, "node_tool_runnable", lambda _path: True)

    assert bt._resolve_npx_bin() == "C:\\hermes\\node\\npx.cmd"


def test_runtime_provisioning_is_npx_only_and_rechecks_node(monkeypatch):
    calls = []
    versions = iter((False, True))
    monkeypatch.setattr(bt, "_agent_browser_node_is_compatible", lambda: next(versions))
    monkeypatch.setattr(
        "hermes_cli.dep_ensure.ensure_dependency",
        lambda dep: calls.append(dep) or True,
    )

    assert bt._ensure_agent_browser_runtime(bt.NPX_AGENT_BROWSER_SENTINEL) is True
    assert calls == ["agent_browser"]


def test_exact_native_agent_browser_does_not_require_node(monkeypatch, tmp_path):
    executable = tmp_path / "agent-browser.exe"
    executable.write_bytes(b"MZ")
    executable.chmod(0o755)
    monkeypatch.setattr(
        bt, "_agent_browser_node_is_compatible",
        lambda: (_ for _ in ()).throw(AssertionError("native executable must not probe Node")),
    )
    monkeypatch.setattr(bt, "_agent_browser_executable_is_native", lambda _path: True)
    monkeypatch.setattr(
        bt.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="agent-browser 0.36.0\n"),
    )

    assert bt._ensure_agent_browser_runtime(str(executable)) is True


def test_stale_native_agent_browser_is_rejected(monkeypatch, tmp_path):
    executable = tmp_path / "agent-browser.exe"
    executable.write_bytes(b"MZ")
    executable.chmod(0o755)
    monkeypatch.setattr(bt, "_agent_browser_executable_is_native", lambda _path: True)
    monkeypatch.setattr(
        bt.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="agent-browser 0.35.1\n"),
    )

    assert bt._ensure_agent_browser_runtime(str(executable)) is False


def test_exact_node_shim_cannot_bypass_node_24_floor(monkeypatch, tmp_path):
    shim = tmp_path / "agent-browser.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")
    shim.chmod(0o755)
    monkeypatch.setattr(bt, "_agent_browser_executable_is_native", lambda _path: False)
    monkeypatch.setattr(bt, "_agent_browser_node_is_compatible", lambda: False)
    monkeypatch.setattr(
        bt.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Node 22 shim must not execute")),
    )

    assert bt._ensure_agent_browser_runtime(str(shim)) is False


def test_exact_node_shim_is_allowed_with_node_24(monkeypatch, tmp_path):
    shim = tmp_path / "agent-browser.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")
    shim.chmod(0o755)
    monkeypatch.setattr(bt, "_agent_browser_executable_is_native", lambda _path: False)
    monkeypatch.setattr(bt, "_agent_browser_node_is_compatible", lambda: True)
    monkeypatch.setattr(
        bt.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="agent-browser 0.36.0\n"),
    )

    assert bt._ensure_agent_browser_runtime(str(shim)) is True


def test_stale_path_candidate_falls_through_to_exact_npx(monkeypatch, tmp_path):
    stale = tmp_path / "agent-browser.cmd"
    stale.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(bt, "_cached_agent_browser", None)
    monkeypatch.setattr(bt, "_agent_browser_resolved", False)
    monkeypatch.setattr(bt, "_merge_browser_path", lambda _path: "")
    monkeypatch.setattr(
        bt.shutil,
        "which",
        lambda command, path=None: str(stale) if command == "agent-browser" else "npx",
    )
    monkeypatch.setattr(bt, "_agent_browser_direct_is_compatible", lambda _path: False)
    monkeypatch.setattr(bt, "_resolve_npx_bin", lambda: "npx")

    assert bt._find_agent_browser(validate=True) == bt.NPX_AGENT_BROWSER_SENTINEL


def test_npx_argv_refuses_node_22_if_a_caller_misses_provisioning(monkeypatch):
    monkeypatch.setattr(bt, "_agent_browser_node_is_compatible", lambda: False)

    try:
        bt._agent_browser_argv(bt.NPX_AGENT_BROWSER_SENTINEL)
    except RuntimeError as exc:
        assert "Node.js 24+" in str(exc)
    else:
        raise AssertionError("npx agent-browser must not execute with Node 22")


def test_agent_browser_node_compatibility_uses_its_declared_floor(monkeypatch):
    monkeypatch.setattr(bt, "find_node_executable", lambda _name: "C:\\node\\node.exe")
    monkeypatch.setattr(
        bt.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="v22.22.0\n"),
    )
    assert bt._agent_browser_node_is_compatible() is False

    monkeypatch.setattr(
        bt.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="v24.11.0\n"),
    )
    assert bt._agent_browser_node_is_compatible() is True
