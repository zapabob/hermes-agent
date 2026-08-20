from pathlib import Path

import yaml

from hermes_cli import config as config_api
from hermes_cli import config_defaults


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_fork_defaults_use_official_config_defaults_api():
    defaults = config_defaults.DEFAULT_CONFIG

    assert config_api.DEFAULT_CONFIG is defaults
    # The distribution leaves the shared selector unset so the provider
    # registry can choose an available keyed backend, or the keyless free
    # tier on a fresh install.  CloakBrowser remains an explicit opt-in.
    assert defaults["web"]["backend"] == ""
    assert defaults["web"]["keyless_fallback"] is True
    assert defaults["browser"]["allow_sensitive_cdp_methods"] is False
    assert defaults["display"]["skin"] == "hakua"
    assert defaults["auxiliary"]["vrchat_autonomy"]["timeout"] == 60
    assert defaults["auxiliary"]["ai_scientist"]["allow_ollama_fallback"] is False
    assert defaults["auxiliary"]["shinka"]["llm_models"] == []
    assert defaults["memory"]["portable_memory_packet_enabled"] is True
    assert defaults["memory"]["sleep"]["enabled"] is False
    assert defaults["logging"]["memory_monitor"]["enabled"] is True
    assert defaults["harness"] == {
        "enabled": True,
        "auto_start": True,
        "host": "127.0.0.1",
        "port": 18794,
        "script_path": "",
    }
    # Upstream increased the default to cover long-running maintenance jobs;
    # assert the current API default rather than preserving the old snapshot.
    assert defaults["cron"]["script_timeout_seconds"] == 3600


def test_fork_extension_env_metadata_remains_discoverable():
    expected = {
        "HYPURA_HARNESS_PORT",
        "HYPURA_HARNESS_HOST",
        "OPENCODE_API_KEY",
        "FREEBUFF_TOKEN",
        "FREEBUFF_PROXY_API_KEY",
        "WORLDMONITOR_API_KEY",
        "WORLDMONITOR_API_BASE",
        "WORLDMONITOR_LOCAL_PORT",
        "SITDECK_EMAIL",
        "SITDECK_PASSWORD",
        "CLOAKBROWSER_PROXY",
    }

    assert expected <= config_defaults.OPTIONAL_ENV_VARS.keys()


def test_operator_stack_uses_unified_delegation_concurrency_api():
    stack = yaml.safe_load(
        (REPO_ROOT / "config" / "operator" / "ai-employee-stack.yaml").read_text(
            encoding="utf-8"
        )
    )

    delegation = stack["delegation"]
    assert delegation["max_concurrent_children"] == 5
    assert "max_async_children" not in delegation
