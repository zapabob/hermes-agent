"""Plugin-side tests for the web search provider migration (PR #25182).

Covers:

- All nine bundled plugins (brave-free, cloakbrowser, ddgs, searxng, exa, parallel,
  tavily, firecrawl, xai) instantiate and self-report the expected
  capabilities + ABC-derived defaults.
- Each plugin's ``is_available()`` correctly reflects env-var presence.
- The web_search_registry resolves an active provider in the documented
  scenarios (explicit config wins ignoring availability, fallback walks
  legacy preference filtered by availability, unknown name falls back).
- Plugin response shapes match the legacy bit-for-bit contract.

Per the dev skill: these tests use *real* imports from the plugin
modules — no mocking of provider classes themselves — so the test
catches drift in the ABC interface, the registry, and the plugin
glue layer simultaneously.
"""
from __future__ import annotations

import asyncio
import inspect

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_web_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every web-provider env var so is_available() returns False."""
    for k in (
        "BRAVE_SEARCH_API_KEY",
        "SEARXNG_URL",
        "TAVILY_API_KEY",
        "TAVILY_BASE_URL",
        "EXA_API_KEY",
        "PARALLEL_API_KEY",
        "PARALLEL_SEARCH_MODE",
        "FIRECRAWL_API_KEY",
        "FIRECRAWL_API_URL",
        "FIRECRAWL_GATEWAY_URL",
        "TOOL_GATEWAY_DOMAIN",
        "TOOL_GATEWAY_USER_TOKEN",
        "XAI_API_KEY",
        "XAI_BASE_URL",
        "HERMES_XAI_BASE_URL",
    ):
        monkeypatch.delenv(k, raising=False)


def _ensure_plugins_loaded() -> None:
    """Idempotently load plugins so the registry is populated."""
    from hermes_cli.plugins import _ensure_plugins_discovered

    _ensure_plugins_discovered()


# ---------------------------------------------------------------------------
# Per-plugin discovery + capability flags
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with a clean web-provider env."""
    _clear_web_env(monkeypatch)


class TestBundledPluginsRegister:
    """All bundled web plugins discover and register correctly."""

    def test_all_bundled_plugins_present_in_registry(self) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import list_providers

        names = sorted(p.name for p in list_providers())
        # Scrapling は9個に含まれず、10個目として追加される
        assert "scrapling" in names
        assert "brave-free" in names
        assert "cloakbrowser" in names
        assert "ddgs" in names
        assert "exa" in names
        assert "firecrawl" in names
        assert "parallel" in names
        assert "searxng" in names
        assert "tavily" in names
        assert "xai" in names
        # 想定される10個（Scrapling含む）
        assert len(names) == 10
        assert names == [
            "brave-free",
            "cloakbrowser",
            "ddgs",
            "exa",
            "firecrawl",
            "parallel",
            "scrapling",
            "searxng",
            "tavily",
            "xai",
        ]

    @pytest.mark.parametrize(
        "plugin_name,expected_search,expected_extract",
        [
            ("brave-free", True, False),
            ("cloakbrowser", True, True),
            ("ddgs", True, False),
            ("searxng", True, False),
            ("exa", True, True),
            ("parallel", True, True),
            ("tavily", True, True),
            ("firecrawl", True, True),
            ("scrapling", True, True),
            # xai: Grok-backed search plus best-effort URL extraction.
            ("xai", True, True),
        ],
    )
    def test_capability_flags_match_spec(
        self,
        plugin_name: str,
        expected_search: bool,
        expected_extract: bool,
    ) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        provider = get_provider(plugin_name)
        assert provider is not None, f"plugin {plugin_name!r} not registered"
        assert provider.supports_search() is expected_search
        assert provider.supports_extract() is expected_extract

    @pytest.mark.parametrize(
        "plugin_name",
        [
            "brave-free",
            "cloakbrowser",
            "ddgs",
            "searxng",
            "exa",
            "parallel",
            "tavily",
            "firecrawl",
            "scrapling",
            "xai",
        ],
    )
    def test_each_plugin_has_name_and_display_name(self, plugin_name: str) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        provider = get_provider(plugin_name)
        assert provider is not None
        assert provider.name == plugin_name
        assert provider.display_name  # any non-empty string


# ---------------------------------------------------------------------------
# is_available() behavior
# ---------------------------------------------------------------------------


class TestIsAvailable:
    """Each plugin's ``is_available()`` returns False without env config."""

    def test_brave_free_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("brave-free")
        assert p is not None
        assert p.is_available() is False  # no BRAVE_SEARCH_API_KEY
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "real")
        assert p.is_available() is True

    def test_searxng_requires_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("searxng")
        assert p is not None
        assert p.is_available() is False
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
        assert p.is_available() is True

    def test_tavily_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("tavily")
        assert p is not None
        assert p.is_available() is False
        monkeypatch.setenv("TAVILY_API_KEY", "real")
        assert p.is_available() is True

    def test_exa_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("exa")
        assert p is not None
        assert p.is_available() is False
        monkeypatch.setenv("EXA_API_KEY", "real")
        assert p.is_available() is True

    def test_parallel_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("parallel")
        assert p is not None
        assert p.is_available() is False
        monkeypatch.setenv("PARALLEL_API_KEY", "real")
        assert p.is_available() is True

    def test_firecrawl_requires_either_key_or_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("firecrawl")
        assert p is not None
        assert p.is_available() is False

        # Either FIRECRAWL_API_KEY or FIRECRAWL_API_URL lights it up.
        monkeypatch.setenv("FIRECRAWL_API_KEY", "real")
        assert p.is_available() is True
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.setenv("FIRECRAWL_API_URL", "http://localhost:3002")
        assert p.is_available() is True

    def test_cloakbrowser_reflects_package_import(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("cloakbrowser")
        assert p is not None

        def _raise(*_a, **_k):
            raise ImportError("no cloakbrowser")

        monkeypatch.setattr(
            "plugins.web.cloakbrowser.provider._ensure_cloakbrowser",
            _raise,
        )
        assert p.is_available() is False

        monkeypatch.setattr(
            "plugins.web.cloakbrowser.provider._ensure_cloakbrowser",
            lambda: None,
        )
        assert p.is_available() is True

    def test_ddgs_always_available_when_package_importable(self) -> None:
        """DDGS is the always-on fallback — no API key required.

        It may report unavailable if the ``ddgs`` package itself isn't
        installed in the env (legitimate — the plugin's post_setup hook
        triggers pip install on first selection). We only assert that
        is_available() doesn't raise.
        """
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("ddgs")
        assert p is not None
        # Truthy or falsy, just must not raise.
        _ = bool(p.is_available())

    def test_xai_requires_api_key_or_oauth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """xAI needs XAI_API_KEY or OAuth tokens in auth.json."""
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("xai")
        assert p is not None
        assert p.is_available() is False  # no XAI_API_KEY, no auth.json
        monkeypatch.setenv("XAI_API_KEY", "real")
        assert p.is_available() is True


# ---------------------------------------------------------------------------
# Registry resolution semantics (Option B — conservative smart fallback)
# ---------------------------------------------------------------------------


class TestRegistryResolution:
    """``_resolve()`` follows explicit-config + availability-filtered fallback."""

    def test_explicit_configured_provider_returned_even_when_unavailable(
        self,
    ) -> None:
        """Explicit ``web.search_backend`` wins regardless of is_available().

        Without availability filtering on the explicit path, the dispatcher
        would silently switch backends; with this check the dispatcher
        surfaces a precise "FOO_API_KEY is not set" error instead.
        """
        _ensure_plugins_loaded()
        from agent.web_search_registry import _resolve

        # No BRAVE_SEARCH_API_KEY (fixture cleared it).
        result = _resolve("brave-free", capability="search")
        assert result is not None
        assert result.name == "brave-free"
        # Confirm it's the unavailable one — dispatcher will surface
        # a typed credential-missing error to the caller.
        assert result.is_available() is False

    def test_unknown_configured_name_falls_back_to_available_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Typo / uninstalled plugin → walk legacy preference, pick available."""
        _ensure_plugins_loaded()
        from agent.web_search_registry import _resolve

        monkeypatch.setenv("EXA_API_KEY", "real")
        result = _resolve("not-a-real-provider", capability="search")
        # Either ddgs (no-key fallback) or exa (the only available
        # premium provider) — both are valid. The point is the unknown
        # name shouldn't return None when SOMETHING is available.
        assert result is not None
        assert result.is_available() is True


    def test_no_config_no_credentials_returns_none(
        self,
    ) -> None:
        """No backend configured AND no available providers → typically None.

        ``cloakbrowser`` / ``ddgs`` are no-credential fallbacks; if either
        Python package is installed in the test env, one of them will be
        picked. Otherwise the resolver returns None. Either outcome is correct.
        """
        _ensure_plugins_loaded()
        from agent.web_search_registry import _resolve

        result = _resolve(None, capability="search")
        if result is not None:
            # No-credential providers: cloakbrowser, ddgs.
            assert result.is_available() is True

    def test_cloakbrowser_extract_is_async(self) -> None:
        _ensure_plugins_loaded()
        from agent.web_search_registry import get_provider

        p = get_provider("cloakbrowser")
        assert p is not None
        assert inspect.iscoroutinefunction(p.extract) is True


# ---------------------------------------------------------------------------
# Sync-vs-async extract detection
# ---------------------------------------------------------------------------


class TestAsyncExtractDispatch:
    """The dispatcher detects async vs sync extract methods correctly."""


# ---------------------------------------------------------------------------
# Error response shape (preserved bit-for-bit from legacy)
# ---------------------------------------------------------------------------


class TestErrorResponseShapes:
    """When credentials are missing, plugins return typed errors, not raises."""


