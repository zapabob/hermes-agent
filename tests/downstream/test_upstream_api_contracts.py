from __future__ import annotations

from agent.local_secretary.write_action_gate import check_write_action
from agent.memory_manager import MemoryManager
from agent.memory_provider import MemoryProvider, RecallStatus
from gateway.platforms.base import BasePlatformAdapter, validate_media_delivery_path
from hermes_cli.config import load_config, load_config_readonly
from hermes_cli.providers import ProviderDef, get_provider, resolve_provider_full
from tools.registry import ToolRegistry, registry

from downstream.compat.hermes import cli, desktop, gateway, memory, providers, tools


def test_cli_facade_uses_official_configuration_authority() -> None:
    assert cli.load_config is load_config
    assert cli.load_config_readonly is load_config_readonly


def test_gateway_facade_uses_official_adapter_and_media_contracts() -> None:
    assert gateway.BasePlatformAdapter is BasePlatformAdapter
    assert gateway.validate_media_delivery_path is validate_media_delivery_path


def test_provider_facade_uses_official_catalogue() -> None:
    assert providers.ProviderDef is ProviderDef
    assert providers.get_provider is get_provider
    assert providers.resolve_provider_full is resolve_provider_full


def test_memory_facade_uses_official_provider_interface() -> None:
    assert memory.MemoryManager is MemoryManager
    assert memory.MemoryProvider is MemoryProvider
    assert memory.RecallStatus is RecallStatus


def test_tool_facade_reuses_the_single_official_registry() -> None:
    assert tools.ToolRegistry is ToolRegistry
    assert tools.registry is registry


def test_desktop_facade_delegates_to_official_server(monkeypatch) -> None:
    import hermes_cli.web_server

    sentinel = object()
    monkeypatch.setattr(
        hermes_cli.web_server,
        "start_server",
        lambda *args, **kwargs: (sentinel, args, kwargs),
    )
    assert desktop.start_server("host", port=9119) == (
        sentinel,
        ("host",),
        {"port": 9119},
    )


def test_local_secretary_preserves_confirmation_boundary() -> None:
    assert check_write_action("gmail_read").ok is True
    publish = check_write_action("x_publish_post")
    assert publish.ok is False
    assert publish.confirmation_required is True
