"""Contracts for the agent-browser-only Node runtime provisioner."""

from pathlib import Path


INSTALL_SH = Path(__file__).resolve().parent.parent / "scripts" / "install.sh"


def _function_body(source: str, name: str) -> str:
    start = source.index(f"{name}() {{")
    remainder = source[start:]
    return remainder[:remainder.index("\n}\n") + 3]


def test_agent_browser_node_gate_is_separate_from_general_node_compatibility() -> None:
    source = INSTALL_SH.read_text(encoding="utf-8")
    agent_body = _function_body(source, "node_satisfies_agent_browser")
    generic_body = _function_body(source, "node_satisfies_build")

    assert '[ "$major" -ge 24 ]' in agent_body
    assert '[ "$major" -eq 22 ] && [ "$minor" -ge 22 ]' in generic_body


def test_ensure_mode_routes_agent_browser_to_its_minimum_major_gate() -> None:
    source = INSTALL_SH.read_text(encoding="utf-8")
    ensure_body = _function_body(source, "ensure_mode")
    runtime_body = _function_body(source, "check_agent_browser_node")

    assert "agent_browser)" in ensure_body
    assert "check_agent_browser_node" in ensure_body
    assert "check_node" in runtime_body
    assert "install_node" in runtime_body
    assert "node_satisfies_agent_browser" in runtime_body
