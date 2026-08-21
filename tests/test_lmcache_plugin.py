"""Tests for LMCache plugin."""

import json
import pytest

from plugins.lmcache import (
    LMCachePlugin,
    get_model_context_lengths_for_prompt,
    lmcache_clear_all,
    lmcache_get_entry,
    lmcache_get_model_context_lengths,
    lmcache_get_optimization_stats,
    lmcache_record_optimization,
    lmcache_remove_entry,
    lmcache_reset_db,
    lmcache_set_entry,
    lmcache_status,
)


@pytest.fixture(autouse=True)
def clean_lmcache_db(tmp_path, monkeypatch):
    """Isolate LMCache database to a temporary directory."""
    monkeypatch.setattr("plugins.lmcache.PLUGIN_DATA_ROOT", tmp_path)
    # Reset singleton
    monkeypatch.setattr("plugins.lmcache._plugin_instance", None)
    plugin = LMCachePlugin()
    monkeypatch.setattr("plugins.lmcache._plugin_instance", plugin)
    yield plugin


def test_lmcache_plugin_basic_crud(clean_lmcache_db):
    plugin = clean_lmcache_db
    # Set entry
    assert plugin.set_cache_entry("test_key", "test_val", ttl=60) is True
    # Get entry
    assert plugin.get_cache_entry("test_key") == "test_val"
    # Status
    status = plugin.get_status()
    assert status["plugin"] == "lmcache"
    assert status["entries"] == 1
    # Remove entry
    assert plugin.remove_cache_entry("test_key") is True
    assert plugin.get_cache_entry("test_key") is None


def test_lmcache_record_optimization_and_context_lengths(clean_lmcache_db):
    plugin = clean_lmcache_db
    # Record optimization stats
    success = plugin.record_optimization(
        model_name="hermes-3-70b",
        context_length=128000,
        ttft_ms=45.5,
        throughput=85.2,
        provider="nous",
    )
    assert success is True

    # Retrieve optimization stats
    stats = plugin.get_optimization_stats()
    assert len(stats) == 1
    assert stats[0]["model_name"] == "hermes-3-70b"
    assert stats[0]["context_length"] == 128000
    assert stats[0]["ttft_ms"] == 45.5
    assert stats[0]["throughput"] == 85.2
    assert stats[0]["provider"] == "nous"

    # Filter by model
    filtered = plugin.get_optimization_stats(model_name="hermes-3-70b")
    assert len(filtered) == 1
    empty_filter = plugin.get_optimization_stats(model_name="nonexistent")
    assert len(empty_filter) == 0

    # Retrieve model context lengths
    lengths = plugin.get_model_context_lengths()
    assert len(lengths) == 1
    assert lengths[0]["model_name"] == "hermes-3-70b"
    assert lengths[0]["provider"] == "nous"
    assert lengths[0]["context_length"] == 128000


def test_lmcache_clear_all_and_reset_db(clean_lmcache_db):
    plugin = clean_lmcache_db
    plugin.set_cache_entry("k1", "v1")
    plugin.set_cache_entry("k2", "v2")
    assert plugin.get_status()["entries"] == 2

    # Clear all cache entries
    assert plugin.clear_all() is True
    assert plugin.get_status()["entries"] == 0

    # Reset DB
    assert plugin.reset_db() is True
    assert plugin.get_status()["entries"] == 0


def test_lmcache_tool_handlers(clean_lmcache_db):
    # Tool: set entry
    res = json.loads(lmcache_set_entry({"key": "tool_k", "value": "tool_v"}))
    assert res["success"] is True

    # Tool: get entry
    res = json.loads(lmcache_get_entry({"key": "tool_k"}))
    assert res["success"] is True
    assert res["value"] == "tool_v"

    # Tool: status
    res = json.loads(lmcache_status())
    assert res["plugin"] == "lmcache"

    # Tool: record optimization
    res = json.loads(
        lmcache_record_optimization({
            "model_name": "claude-3-7-sonnet",
            "context_length": 200000,
            "ttft_ms": 120.0,
            "throughput": 60.0,
            "provider": "anthropic",
        })
    )
    assert res["success"] is True

    # Tool: get optimization stats
    res = json.loads(lmcache_get_optimization_stats())
    assert res["success"] is True
    assert len(res["stats"]) == 1

    # Tool: get model context lengths
    res = json.loads(lmcache_get_model_context_lengths())
    assert res["success"] is True
    assert len(res["models"]) == 1

    # Tool: remove entry
    res = json.loads(lmcache_remove_entry({"key": "tool_k"}))
    assert res["success"] is True

    # Tool: clear all
    res = json.loads(lmcache_clear_all())
    assert res["success"] is True

    # Tool: reset db
    res = json.loads(lmcache_reset_db())
    assert res["success"] is True


def test_get_model_context_lengths_for_prompt(clean_lmcache_db):
    plugin = clean_lmcache_db
    plugin.record_optimization(
        model_name="deepseek-r1",
        context_length=64000,
        ttft_ms=80.0,
        throughput=40.0,
        provider="deepseek",
    )

    prompt_str = get_model_context_lengths_for_prompt()
    assert "【モデルコンテキスト長情報】" in prompt_str
    assert "deepseek-r1" in prompt_str
    assert "64000" in prompt_str
