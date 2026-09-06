"""Tests for agent/anthropic_adapter.py — Anthropic Messages API adapter."""

import json
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from agent.prompt_caching import apply_anthropic_cache_control
from agent.anthropic_adapter import build_anthropic_client, build_anthropic_bedrock_client, build_anthropic_kwargs
from agent.anthropic_credentials import _is_oauth_token, _refresh_oauth_token, _write_claude_code_credentials, is_claude_code_token_valid, read_claude_code_credentials, resolve_anthropic_token, run_oauth_setup_token
from agent.anthropic_endpoints import _is_azure_anthropic_endpoint
from agent.anthropic_message_convert import _to_plain_data, convert_messages_to_anthropic, convert_tools_to_anthropic, normalize_model_name
from agent.transports import get_transport

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


class TestIsOAuthToken:
    def test_setup_token(self):
        assert _is_oauth_token("«redacted:sk-…»") is True

    def test_api_key(self):
        assert _is_oauth_token("«redacted:sk-…»") is False


class TestBuildAnthropicClient:

    def test_api_key_uses_api_key(self):
        with patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk:
            build_anthropic_client("sk-ant-api03-something")
            kwargs = mock_sdk.Anthropic.call_args[1]
            assert kwargs["api_key"] == "sk-ant-api03-something"
            assert "auth_token" not in kwargs
            # API key auth should still get common betas
            betas = kwargs["default_headers"]["anthropic-beta"]
            assert "interleaved-thinking-2025-05-14" in betas
            assert "context-1m-2025-08-07" not in betas
            assert "oauth-2025-04-20" not in betas  # OAuth-only beta NOT present
            assert "claude-code-20250219" not in betas  # OAuth-only beta NOT present

    def test_opencode_endpoint_gets_attribution_headers(self):
        """OpenCode identifies clients by request headers, like OpenRouter.

        The OpenAI-wire paths get HTTP-Referer / X-Title / User-Agent from
        profile.default_headers. The Anthropic Messages route builds its
        client here and must merge the same set.
        """
        with patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk:
            build_anthropic_client(
                "sk-ant-api03-something",
                base_url="https://opencode.ai/zen/go/v1",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            assert headers["HTTP-Referer"] == "https://hermes-agent.nousresearch.com"
            assert headers["X-Title"] == "Hermes Agent"
            assert headers["User-Agent"].startswith("HermesAgent/")
            # Auth branch is unchanged: x-api-key via api_key, betas kept.
            assert kwargs["api_key"] == "sk-ant-api03-something"
            assert "anthropic-beta" in headers

    def test_minimax_anthropic_endpoint_uses_bearer_auth_for_regular_api_keys(self):
        with patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk:
            build_anthropic_client(
                "minimax-secret-123",
                base_url="https://api.minimax.io/anthropic",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            assert kwargs["auth_token"] == "minimax-secret-123"
            assert "api_key" not in kwargs
            assert kwargs["default_headers"] == {
                "anthropic-beta": "interleaved-thinking-2025-05-14"
            }

    def test_azure_foundry_anthropic_endpoint_uses_bearer_auth(self):
        """Azure AI Foundry's /anthropic endpoint requires Authorization: Bearer.

        Regression test for #26970: without this, builds set api_key (x-api-key)
        and the endpoint returns HTTP 401. Also verifies that Azure retains the
        1M-context beta even though it now matches `_requires_bearer_auth`.
        """
        with patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk:
            build_anthropic_client(
                "azure-foundry-secret-123",
                base_url="https://my-resource.openai.azure.com/anthropic",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            assert kwargs["auth_token"] == "azure-foundry-secret-123"
            assert "api_key" not in kwargs
            # Azure endpoints still get the api-version query param plumbing.
            assert kwargs.get("default_query") == {"api-version": "2025-04-15"}
            # Azure keeps the 1M-context beta (it's not MiniMax).
            betas = kwargs["default_headers"]["anthropic-beta"]
            assert "context-1m-2025-08-07" in betas

    def test_palantir_foundry_anthropic_endpoint_uses_bearer_auth(self):
        """Palantir Foundry's LLM proxy requires Authorization: Bearer.

        Regression test for PR #36043: Palantir's
        ``<org>.palantirfoundry.com/api/v2/llm/proxy/anthropic`` endpoint
        rejects x-api-key with 401 — the SDK must be built with auth_token.
        """
        with patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk:
            build_anthropic_client(
                "foundry-secret-123",
                base_url="https://acme.palantirfoundry.com/api/v2/llm/proxy/anthropic",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            assert kwargs["auth_token"] == "foundry-secret-123"
            assert "api_key" not in kwargs

    def test_disables_sdk_retries_for_api_key(self):
        """#26293: the SDK's default max_retries=2 ignores Retry-After and
        double-retries inside hermes's outer loop. We delegate retry entirely
        to the outer loop, so the client must be built with max_retries=0."""
        with patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk:
            build_anthropic_client("sk-ant-api03-something")
            kwargs = mock_sdk.Anthropic.call_args[1]
            assert kwargs["max_retries"] == 0

    # ------------------------------------------------------------------ #
    # Registered-profile default_headers merge (PR #104052)
    # ------------------------------------------------------------------ #

    def test_registered_profile_default_headers_merged(self):
        """A registered provider profile whose base_url prefix matches the
        Anthropic endpoint should have its default_headers merged into the
        client. Auth-branch headers (betas) must still win on key conflict.

        NOTE: _base_client_kwargs strips trailing /v1 from the endpoint URL,
        so the normalized_base_url used for matching is without /v1. The
        profile's base_url must also be without /v1 for the startswith check
        to work (or the profile base_url must be a shorter prefix)."""
        mock_profile = SimpleNamespace(
            base_url="https://api.my-custom-anthro.com",
            default_headers={"X-Workspace-Id": "ws-123", "X-Tenant": "acme"},
        )
        with (
            patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk,
            patch("providers.list_providers", return_value=[mock_profile]),
        ):
            build_anthropic_client(
                "sk-ant...cret",
                base_url="https://api.my-custom-anthro.com/v1",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            # Profile headers present
            assert headers["X-Workspace-Id"] == "ws-123"
            assert headers["X-Tenant"] == "acme"
            # Auth-branch headers still present (betas)
            assert "anthropic-beta" in headers

    def test_registered_profile_headers_do_not_override_auth_headers(self):
        """When a profile's default_headers and the auth branch set the same
        key, the auth-branch value wins (merged via _merged.update(headers))."""
        mock_profile = SimpleNamespace(
            base_url="https://api.override-test.com",
            default_headers={"anthropic-beta": "overridden-by-auth"},
        )
        with (
            patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk,
            patch("providers.list_providers", return_value=[mock_profile]),
        ):
            build_anthropic_client(
                "sk-ant...cret",
                base_url="https://api.override-test.com/v1",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            # Auth-branch beta wins, not the profile's
            assert "interleaved-thinking-2025-05-14" in headers["anthropic-beta"]
            assert "overridden-by-auth" not in headers["anthropic-beta"]

    def test_no_matching_profile_skips_header_merge(self):
        """When no registered profile's base_url matches the endpoint, the
        client headers are unchanged (no default_headers merge)."""
        mock_profile = SimpleNamespace(
            base_url="https://api.unrelated.com",
            default_headers={"X-Workspace-Id": "ws-123"},
        )
        with (
            patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk,
            patch("providers.list_providers", return_value=[mock_profile]),
        ):
            build_anthropic_client(
                "sk-ant...cret",
                base_url="https://api.my-custom-anthro.com/v1",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            # Unrelated profile's header NOT present
            assert "X-Workspace-Id" not in headers
            # Standard betas still present
            assert "anthropic-beta" in headers

    def test_profile_without_default_headers_skips_merge(self):
        """A matching profile that has no default_headers (None or empty)
        should not crash and should not inject anything."""
        mock_profile = SimpleNamespace(
            base_url="https://api.no-headers.com",
            default_headers=None,
        )
        with (
            patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk,
            patch("providers.list_providers", return_value=[mock_profile]),
        ):
            build_anthropic_client(
                "sk-ant...cret",
                base_url="https://api.no-headers.com/v1",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            assert "anthropic-beta" in headers

    def test_no_base_url_skips_profile_merge(self):
        """When no base_url is provided, the profile merge block is skipped
        entirely (normalized_base_url is empty)."""
        mock_profile = SimpleNamespace(
            base_url="https://api.irrelevant.com",
            default_headers={"X-Workspace-Id": "ws-123"},
        )
        with (
            patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk,
            patch("providers.list_providers", return_value=[mock_profile]),
        ):
            build_anthropic_client("sk-ant...cret")
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            assert "X-Workspace-Id" not in headers
            assert "anthropic-beta" in headers

    def test_profile_merge_exception_does_not_crash(self):
        """If list_providers or the merge loop raises, the try/except catches
        it and the client is still built normally."""
        with (
            patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk,
            patch("providers.list_providers", side_effect=RuntimeError("boom")),
        ):
            # Should not raise
            build_anthropic_client(
                "sk-ant...cret",
                base_url="https://api.anything.com/v1",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            assert "anthropic-beta" in headers

    def test_profile_base_url_prefix_match(self):
        """The merge uses startswith matching, so a profile with base_url
        'https://api.gateway.com' should match an endpoint at
        'https://api.gateway.com/anthropic/v1'."""
        mock_profile = SimpleNamespace(
            base_url="https://api.gateway.com",
            default_headers={"X-Gateway-Token": "tok-abc"},
        )
        with (
            patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk,
            patch("providers.list_providers", return_value=[mock_profile]),
        ):
            build_anthropic_client(
                "sk-ant...cret",
                base_url="https://api.gateway.com/anthropic/v1",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            assert headers["X-Gateway-Token"] == "tok-abc"

    def test_first_match_wins_no_second_merge(self):
        """Only the first matching profile is used; subsequent matches are
        skipped (break after first match)."""
        profile_a = SimpleNamespace(
            base_url="https://api.shared.com",
            default_headers={"X-Source": "profile-a"},
        )
        profile_b = SimpleNamespace(
            base_url="https://api.shared.com",
            default_headers={"X-Source": "profile-b"},
        )
        with (
            patch("agent.anthropic_adapter._anthropic_sdk") as mock_sdk,
            patch("providers.list_providers", return_value=[profile_a, profile_b]),
        ):
            build_anthropic_client(
                "sk-ant...cret",
                base_url="https://api.shared.com/v1",
            )
            kwargs = mock_sdk.Anthropic.call_args[1]
            headers = kwargs["default_headers"]
            # First match wins
            assert headers["X-Source"] == "profile-a"


class TestReadClaudeCodeCredentials:
    @pytest.fixture(autouse=True)
    def no_keychain(self, monkeypatch):
        monkeypatch.setattr(
            "agent.anthropic_credentials._read_claude_code_credentials_from_keychain",
            lambda: None,
        )

    def test_reads_valid_credentials(self, tmp_path, monkeypatch):
        cred_file = tmp_path / ".claude" / ".credentials.json"
        cred_file.parent.mkdir(parents=True)
        cred_file.write_text(json.dumps({
            "claudeAiOauth": {
                "accessToken": "sk-ant-api03-something",
                "refreshToken": "sk-ant-api03-something",
                "expiresAt": int(time.time() * 1000) + 3600_000,
            }
        }))
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        creds = read_claude_code_credentials()
        assert creds is not None
        assert creds["accessToken"] == "sk-ant-api03-something"
        assert creds["refreshToken"] == "sk-ant-api03-something"
        assert creds["source"] == "claude_code_credentials_file"

    def test_ignores_primary_api_key_for_native_anthropic_resolution(self, tmp_path, monkeypatch):
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text(json.dumps({"primaryApiKey": "sk-ant-api03-something"}))
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)

        creds = read_claude_code_credentials()
        assert creds is None


class TestIsClaudeCodeTokenValid:
    def test_valid_token(self):
        creds = {"accessToken": "tok", "expiresAt": int(time.time() * 1000) + 3600_000}
        assert is_claude_code_token_valid(creds) is True

    def test_expired_token(self):
        creds = {"accessToken": "tok", "expiresAt": int(time.time() * 1000) - 3600_000}
        assert is_claude_code_token_valid(creds) is False

    def test_no_expiry_but_has_token(self):
        creds = {"accessToken": "tok", "expiresAt": 0}
        assert is_claude_code_token_valid(creds) is True


class TestResolveAnthropicToken:
    def _assert_not_called(*_args, **_kwargs):
        raise AssertionError("should not be called when API key is present")

    def test_prefers_oauth_token_over_api_key(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-something")
        monkeypatch.setenv("ANTHROPIC_TOKEN", "sk-ant-api03-something")
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        assert resolve_anthropic_token() == "sk-ant-api03-something"

    def test_does_not_resolve_primary_api_key_as_native_anthropic_token(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        (tmp_path / ".claude.json").write_text(json.dumps({"primaryApiKey": "sk-ant-api03-something"}))
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)

        assert resolve_anthropic_token() is None

    def test_falls_back_to_api_key_when_no_oauth_sources_exist(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant...ykey")
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        assert resolve_anthropic_token() == "sk-ant...ykey"

    def test_api_key_wins_over_auto_discovered_claude_code_credentials(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant...ykey")
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        cred_file = tmp_path / ".claude" / ".credentials.json"
        cred_file.parent.mkdir(parents=True)
        cred_file.write_text(json.dumps({
            "claudeAiOauth": {
                "accessToken": "cc-auto-token",
                "refreshToken": "refresh",
                "expiresAt": int(time.time() * 1000) + 3600_000,
            }
        }))
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)

        assert resolve_anthropic_token() == "sk-ant...ykey"

    def test_api_key_path_does_not_read_auto_discovered_credentials(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant...ykey")
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.setattr(
            "agent.anthropic_credentials.read_claude_code_credentials",
            self._assert_not_called,
        )

        assert resolve_anthropic_token() == "sk-ant...ykey"

    def test_falls_back_to_claude_code_credentials(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        cred_file = tmp_path / ".claude" / ".credentials.json"
        cred_file.parent.mkdir(parents=True)
        cred_file.write_text(json.dumps({
            "claudeAiOauth": {
                "accessToken": "cc-auto-token",
                "refreshToken": "refresh",
                "expiresAt": int(time.time() * 1000) + 3600_000,
            }
        }))
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        assert resolve_anthropic_token() == "cc-auto-token"

    def test_falls_back_to_anthropic_credential_pool_oauth(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        # Isolate source #5 (credential_pool): ensure source #4 (Claude Code
        # creds, incl. the macOS keychain read which Path.home does not cover)
        # returns nothing, mirroring a Hermes-PKCE-only setup.
        monkeypatch.setattr("agent.anthropic_credentials.read_claude_code_credentials", lambda: None)

        pool_entry = SimpleNamespace(
            auth_type="oauth",
            access_token="pool-oauth-token",
        )
        pool = SimpleNamespace(
            _available_entries=lambda **_kwargs: ([pool_entry], []),
        )
        monkeypatch.setattr("agent.credential_pool.load_pool", lambda provider: pool)

        assert resolve_anthropic_token() == "pool-oauth-token"

    def test_api_key_wins_over_anthropic_credential_pool_oauth(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant...ykey")
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        monkeypatch.setattr(
            "agent.anthropic_credentials.read_claude_code_credentials",
            self._assert_not_called,
        )
        monkeypatch.setattr(
            "agent.credential_pool.load_pool",
            self._assert_not_called,
        )

        assert resolve_anthropic_token() == "sk-ant...ykey"

    def test_pool_entry_with_null_access_token_does_not_crash(self, monkeypatch, tmp_path):
        """A persisted OAuth entry with access_token=None must not crash the
        resolver (None.strip() would escape the helper's try/excepts and take
        down the whole resolver incl. the ANTHROPIC_API_KEY fallback). It should
        be skipped and the api-key fallback (source #3) should win."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant...ykey")
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        monkeypatch.setattr("agent.anthropic_credentials.read_claude_code_credentials", lambda: None)

        broken_entry = SimpleNamespace(auth_type="oauth", access_token=None)
        pool = SimpleNamespace(
            _available_entries=lambda **_kwargs: ([broken_entry], []),
        )
        monkeypatch.setattr("agent.credential_pool.load_pool", lambda provider: pool)

        # Must fall through to source #3 (ANTHROPIC_API_KEY), not raise.
        assert resolve_anthropic_token() == "sk-ant...ykey"

    def test_pool_api_key_only_entry_is_not_returned_as_token(self, monkeypatch, tmp_path):
        """resolve_anthropic_token() returns an OAuth bearer token; a pool entry
        whose auth_type is api_key (not oauth) must NOT be returned from the pool
        path — those are consumed via the aux client's _pool_runtime_api_key
        lane, a different resolution concern."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        monkeypatch.setattr("agent.anthropic_credentials.read_claude_code_credentials", lambda: None)

        api_key_entry = SimpleNamespace(auth_type="api_key", access_token="sk-ant-api03-something")
        pool = SimpleNamespace(
            _available_entries=lambda **_kwargs: ([api_key_entry], []),
        )
        monkeypatch.setattr("agent.credential_pool.load_pool", lambda provider: pool)

        # No OAuth entry and no other source → None (the api_key entry is ignored here).
        assert resolve_anthropic_token() is None

    def test_pool_resolution_is_read_only(self, monkeypatch, tmp_path):
        """The resolver must enumerate the pool read-only — clear_expired and
        refresh must both be False so a bare resolve never writes auth.json or
        triggers a network refresh from diagnostic call sites (#50108 MED)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        monkeypatch.setattr("agent.anthropic_credentials.read_claude_code_credentials", lambda: None)

        captured = {}
        pool_entry = SimpleNamespace(auth_type="oauth", access_token="pool-oauth-token")

        def _available_entries(**kwargs):
            captured.update(kwargs)
            return ([pool_entry], [])

        pool = SimpleNamespace(_available_entries=_available_entries)
        monkeypatch.setattr("agent.credential_pool.load_pool", lambda provider: pool)

        assert resolve_anthropic_token() == "pool-oauth-token"
        assert captured == {"clear_expired": False, "refresh": False}

    def test_prefers_refreshable_claude_code_credentials_over_static_anthropic_token(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_TOKEN", "sk-ant-api03-something")
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        cred_file = tmp_path / ".claude" / ".credentials.json"
        cred_file.parent.mkdir(parents=True)
        cred_file.write_text(json.dumps({
            "claudeAiOauth": {
                "accessToken": "cc-auto-token",
                "refreshToken": "refresh-token",
                "expiresAt": int(time.time() * 1000) + 3600_000,
            }
        }))
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)

        assert resolve_anthropic_token() == "cc-auto-token"


class TestRefreshOauthToken:
    def test_returns_none_without_refresh_token(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        # Neutralize live Claude Code sources (macOS Keychain + ~/.claude file)
        # so the adopt-already-refreshed branch can't short-circuit with a real
        # credential on a dev/CI machine that happens to have Claude Code creds.
        monkeypatch.setattr(
            "agent.anthropic_credentials.read_claude_code_credentials", lambda: None
        )
        creds = {"accessToken": "expired", "refreshToken": "", "expiresAt": 0}
        assert _refresh_oauth_token(creds) is None

    def test_successful_refresh(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        monkeypatch.setattr(
            "agent.anthropic_credentials.read_claude_code_credentials", lambda: None
        )

        creds = {
            "accessToken": "old-token",
            "refreshToken": "refresh-123",
            "expiresAt": int(time.time() * 1000) - 3600_000,
        }

        mock_response = json.dumps({
            "access_token": "new-token-abc",
            "refresh_token": "new-refresh-456",
            "expires_in": 7200,
        }).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=MagicMock(
                read=MagicMock(return_value=mock_response)
            ))
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_ctx

            result = _refresh_oauth_token(creds)

        assert result == "new-token-abc"
        # Verify credentials were written back
        cred_file = tmp_path / ".claude" / ".credentials.json"
        assert cred_file.exists()
        written = json.loads(cred_file.read_text())
        assert written["claudeAiOauth"]["accessToken"] == "new-token-abc"
        assert written["claudeAiOauth"]["refreshToken"] == "new-refresh-456"

    def test_failed_refresh_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        monkeypatch.setattr(
            "agent.anthropic_credentials.read_claude_code_credentials", lambda: None
        )
        creds = {
            "accessToken": "old",
            "refreshToken": "refresh-123",
            "expiresAt": 0,
        }

        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            assert _refresh_oauth_token(creds) is None


class TestWriteClaudeCodeCredentials:
    def test_writes_new_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        _write_claude_code_credentials("tok", "ref", 12345)
        cred_file = tmp_path / ".claude" / ".credentials.json"
        assert cred_file.exists()
        data = json.loads(cred_file.read_text())
        assert data["claudeAiOauth"]["accessToken"] == "tok"
        assert data["claudeAiOauth"]["refreshToken"] == "ref"
        assert data["claudeAiOauth"]["expiresAt"] == 12345

    def test_preserves_existing_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        cred_dir = tmp_path / ".claude"
        cred_dir.mkdir()
        cred_file = cred_dir / ".credentials.json"
        cred_file.write_text(json.dumps({"otherField": "keep-me"}))
        _write_claude_code_credentials("new-tok", "new-ref", 99999)
        data = json.loads(cred_file.read_text())
        assert data["otherField"] == "keep-me"
        assert data["claudeAiOauth"]["accessToken"] == "new-tok"

    @pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX mode bits not enforced on Windows")
    def test_credentials_file_created_with_0o600(self, tmp_path, monkeypatch):
        """Refreshed Claude Code credentials must land on disk at 0o600.

        Regression for the TOCTOU race where ``write_text`` + ``replace``
        + post-write ``chmod`` left both the temp file and the destination
        briefly readable at the process umask (commonly 0o644). Mirrors
        the fix shipped in #19673 (google_oauth) and #21148 (mcp_oauth).
        """
        import stat as _stat
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)
        _write_claude_code_credentials("tok", "ref", 12345)

        cred_file = tmp_path / ".claude" / ".credentials.json"
        assert cred_file.exists()
        mode = _stat.S_IMODE(cred_file.stat().st_mode)
        assert mode == 0o600, f"creds file mode {oct(mode)} != 0o600 — TOCTOU race regressed"


class TestResolveWithRefresh:
    def test_auto_refresh_on_expired_creds(self, monkeypatch, tmp_path):
        """When cred file has expired token + refresh token, auto-refresh is attempted."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        # Set up expired creds with a refresh token
        cred_file = tmp_path / ".claude" / ".credentials.json"
        cred_file.parent.mkdir(parents=True)
        cred_file.write_text(json.dumps({
            "claudeAiOauth": {
                "accessToken": "expired-token",
                "refreshToken": "refresh-123",
                "expiresAt": 0,
            }
        }))
        monkeypatch.setattr("agent.anthropic_credentials.Path.home", lambda: tmp_path)

        mock_response = json.dumps({
            "access_token": "new-token-abc",
            "refresh_token": "new-refresh-456",
            "expires_in": 7200,
        }).encode()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=MagicMock(
                read=MagicMock(return_value=mock_response)
            ))
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_ctx

            token = resolve_anthropic_token()

        assert token == "new-token-abc"