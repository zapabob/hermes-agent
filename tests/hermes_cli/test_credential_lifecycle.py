"""E2E tests for the unified provider-credential lifecycle (#51071 #59761 #62269).

A provider API key can live in .env, auth.json's credential_pool, and
config.yaml mirrors at once. These tests drive the REAL dashboard endpoint
handlers (PUT/DELETE /api/env) against real on-disk fixtures in a temp
HERMES_HOME (tests/conftest.py isolation) and assert every store agrees
afterwards.

All fake secrets are constructed at runtime so no key-shaped literal ever
lands in the repo.
"""

import json

import pytest
from fastapi.testclient import TestClient

from hermes_cli.web_server import _SESSION_TOKEN, app

client = TestClient(app)
HEADERS = {"X-Hermes-Session-Token": _SESSION_TOKEN}

# Runtime-constructed fake credentials (never literal key-shaped strings).
FAKE_ZAI_KEY = "zk-" + "a" * 24
FAKE_OAUTH_TOKEN = "oa-" + "b" * 24
NEW_KEY = "zk-" + "c" * 24


@pytest.fixture
def hermes_home(monkeypatch, tmp_path):
    """Fresh HERMES_HOME with .env + auth.json + config.yaml fixtures."""
    home = tmp_path / "cred_home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    from hermes_cli.config import invalidate_env_cache

    invalidate_env_cache()
    return home


def _write_env(home, **pairs):
    home.joinpath(".env").write_text(
        "".join(f"{k}={v}\n" for k, v in pairs.items()), encoding="utf-8"
    )
    from hermes_cli.config import invalidate_env_cache

    invalidate_env_cache()


def _write_auth(home, pool):
    home.joinpath("auth.json").write_text(
        json.dumps({"credential_pool": pool}), encoding="utf-8"
    )


def _read_auth(home):
    return json.loads(home.joinpath("auth.json").read_text(encoding="utf-8"))


def _zai_pool_fixture():
    """One env-seeded API-key entry plus one OAuth entry for the same provider."""
    return {
        "zai": [
            {
                "id": "e1",
                "label": "env",
                "auth_type": "api_key",
                "priority": 0,
                "source": "env:ZAI_API_KEY",
                "access_token": FAKE_ZAI_KEY,
            },
            {
                "id": "o1",
                "label": "oauth",
                "auth_type": "oauth",
                "priority": 0,
                "source": "device_code",
                "access_token": FAKE_OAUTH_TOKEN,
                "refresh_token": "rt-" + "d" * 16,
            },
        ]
    }


# ---------------------------------------------------------------------------
# DELETE — #51071 / #59761: stale credential_pool entries must be pruned
# ---------------------------------------------------------------------------




def test_delete_clears_provider_models_cache(hermes_home):
    _write_env(hermes_home, ZAI_API_KEY=FAKE_ZAI_KEY)
    _write_auth(hermes_home, {"zai": [_zai_pool_fixture()["zai"][0]]})
    cache_path = hermes_home / "provider_models_cache.json"
    cache_path.write_text(
        json.dumps({"zai": {"models": ["glm-5"], "ts": 0}}), encoding="utf-8"
    )

    resp = client.request(
        "DELETE", "/api/env", json={"key": "ZAI_API_KEY"}, headers=HEADERS
    )
    assert resp.status_code == 200
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        assert "zai" not in cache


def _write_config(home, text):
    home.joinpath("config.yaml").write_text(text, encoding="utf-8")


def test_update_removes_config_yaml_model_mirror(hermes_home):
    old = "sk-oe-" + "f" * 24
    new = "sk-oe-" + "g" * 24
    _write_env(hermes_home, OPENAI_API_KEY=old)
    _write_config(
        hermes_home,
        "model:\n"
        "  provider: custom\n"
        "  default: my-model\n"
        "  base_url: https://llm.example.test/v1\n"
        f"  api_key: {old}\n",
    )

    resp = client.put(
        "/api/env", json={"key": "OPENAI_API_KEY", "value": new}, headers=HEADERS
    )
    assert resp.status_code == 200
    assert "model.api_key" in resp.json().get("config_updates", [])

    cfg_text = hermes_home.joinpath("config.yaml").read_text(encoding="utf-8")
    assert old not in cfg_text, "stale old key left in config.yaml (#62269)"
    assert new not in cfg_text, "new key copied into config.yaml"
    assert "api_key:" not in cfg_text

    from hermes_cli.config import load_env

    assert load_env()["OPENAI_API_KEY"] == new


def test_first_save_removes_matching_legacy_config_secret(hermes_home):
    canary = "nvapi-" + "q" * 24
    _write_config(
        hermes_home,
        "model:\n"
        "  provider: nvidia\n"
        "  default: meta/llama-3.1-8b-instruct\n"
        f"  api_key: {canary}\n",
    )

    from hermes_cli.credential_lifecycle import save_provider_env_credential

    result = save_provider_env_credential("NVIDIA_API_KEY", canary)

    assert "model.api_key" in result["config_updates"]
    assert canary not in hermes_home.joinpath("config.yaml").read_text(encoding="utf-8")


def test_save_is_scoped_to_active_profile(monkeypatch, tmp_path):
    from hermes_cli.config import invalidate_env_cache, load_env
    from hermes_cli.credential_lifecycle import save_provider_env_credential

    first = tmp_path / "profiles" / "first"
    second = tmp_path / "profiles" / "second"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    canary = "nvapi-" + "p" * 24

    monkeypatch.setenv("HERMES_HOME", str(first))
    invalidate_env_cache()
    save_provider_env_credential("NVIDIA_API_KEY", canary)

    monkeypatch.setenv("HERMES_HOME", str(second))
    invalidate_env_cache()

    assert "NVIDIA_API_KEY" not in load_env()
    assert canary in first.joinpath(".env").read_text(encoding="utf-8")
    assert not second.joinpath(".env").exists()
    assert not first.joinpath("config.yaml").exists()




# ---------------------------------------------------------------------------
# Suppression round-trip: delete sticks, re-add lifts it
# ---------------------------------------------------------------------------
