"""Provider rotation keeps automatic retries heterogeneous and strict pins strict."""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from agent.web_search_provider import WebSearchProvider


class _Provider(WebSearchProvider):
    def __init__(self, name: str, *, available: bool = True, keyless: bool = False):
        self._name = name
        self._available = available
        self._keyless = keyless

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    def is_keyless_available(self) -> bool:
        return self._keyless

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return True

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        return {"success": True, "data": {"web": [{"url": query, "title": self.name, "description": ""}]}}

    def extract(self, urls: List[str], **kwargs: Any) -> List[Dict[str, Any]]:
        return [{"url": url, "title": self.name, "content": "ok"} for url in urls]


@pytest.fixture(autouse=True)
def _restore_registry():
    import agent.web_search_registry as registry

    providers = dict(registry._providers)
    scoped = {key: dict(value) for key, value in registry._scoped_providers.items()}
    yield
    registry._providers.clear()
    registry._providers.update(providers)
    registry._scoped_providers.clear()
    registry._scoped_providers.update(scoped)


def test_automatic_fallback_excludes_primary_and_preserves_cloakbrowser_default(monkeypatch):
    import agent.web_search_registry as registry

    monkeypatch.setattr(registry, "_read_config_key", lambda *path: None)
    registry.register_provider(_Provider("cloakbrowser", available=True))
    registry.register_provider(_Provider("parallel", available=True))

    result = registry.get_fallback_provider("search", exclude="cloakbrowser")

    assert result is not None
    assert result.name == "parallel"


def test_distribution_default_is_auto_with_cloakbrowser_primary(monkeypatch):
    import agent.web_search_registry as registry
    from hermes_cli.config_defaults import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["web"]["backend"] == ""
    registry.register_provider(_Provider("cloakbrowser", available=True))
    registry.register_provider(_Provider("parallel", available=True))
    monkeypatch.setattr(registry, "_read_config_key", lambda *path: None)

    primary = registry._resolve(None, capability="search")
    retry = registry.get_fallback_provider("search", exclude=primary.name)

    assert primary is not None and primary.name == "cloakbrowser"
    assert retry is not None and retry.name == "parallel"


def test_automatic_fallback_reaches_keyless_runner_up(monkeypatch):
    import agent.web_search_registry as registry

    monkeypatch.setattr(registry, "_read_config_key", lambda *path: None)
    registry.register_provider(_Provider("cloakbrowser", available=True))
    registry.register_provider(_Provider("exa", available=False, keyless=True))
    monkeypatch.setattr(registry, "_keyless_preference", lambda: ("exa", "parallel"))

    result = registry.get_fallback_provider("extract", exclude="cloakbrowser")

    assert result is not None
    assert result.name == "exa"


def test_extract_rotation_has_the_same_primary_and_runner_up_contract(monkeypatch):
    import agent.web_search_registry as registry

    monkeypatch.setattr(registry, "_read_config_key", lambda *path: None)
    registry.register_provider(_Provider("cloakbrowser", available=True))
    registry.register_provider(_Provider("exa", available=True))

    primary = registry._resolve(None, capability="extract")
    retry = registry.get_fallback_provider("extract", exclude=primary.name)

    assert primary is not None and primary.name == "cloakbrowser"
    assert retry is not None and retry.name == "exa"


def test_explicit_backend_does_not_rotate(monkeypatch):
    import agent.web_search_registry as registry

    monkeypatch.setattr(
        registry,
        "_read_config_key",
        lambda *path: "cloakbrowser" if path in (("web", "backend"), ("web", "search_backend")) else None,
    )
    registry.register_provider(_Provider("parallel", available=True))

    assert registry.get_fallback_provider("search", exclude="cloakbrowser") is None
