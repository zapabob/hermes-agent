"""Unit tests for the on-disk MCP schema cache (tools/mcp_schema_cache.py).

The module landed in #56832's extraction without its tests; these cover the
fingerprint keying, read/write round-trip, and invalidation behavior.
"""

import tools.mcp_schema_cache as msc


class TestConfigFingerprint:
    def test_stable_for_same_config(self):
        cfg = {"command": "npx", "args": ["-y", "@playwright/mcp"]}
        assert msc.config_fingerprint(cfg) == msc.config_fingerprint(dict(cfg))

    def test_changes_when_connection_config_changes(self):
        base = {"command": "npx", "args": ["-y", "@playwright/mcp"]}
        assert msc.config_fingerprint(base) != msc.config_fingerprint(
            {**base, "args": ["-y", "@playwright/mcp", "--headless"]}
        )
        assert msc.config_fingerprint(base) != msc.config_fingerprint(
            {**base, "command": "uvx"}
        )
        assert msc.config_fingerprint(base) != msc.config_fingerprint(
            {**base, "tools": {"include": ["a"]}}
        )

    def test_ignores_non_connection_keys(self):
        base = {"command": "npx", "args": []}
        assert msc.config_fingerprint(base) == msc.config_fingerprint(
            {**base, "timeout": 5, "enabled": True, "lazy": True}
        )


class TestCacheRoundTrip:
    def _isolate(self, monkeypatch, tmp_path):
        monkeypatch.setattr(msc, "_cache_path", lambda: tmp_path / "cache.json")

    def test_write_then_read_with_matching_fingerprint(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        tools = [{"name": "t1", "description": "d", "inputSchema": {"type": "object"}}]
        msc.write_cache_entry("srv", "fp1", tools=tools, utility_tools=[])
        entry = msc.get_cached_entry("srv", "fp1")
        assert entry is not None
        assert msc.tools_from_cache_entry(entry) == tools
        assert msc.utility_tools_from_cache_entry(entry) == []
        assert msc.has_cached_entry("srv", "fp1")

    def test_fingerprint_mismatch_returns_none(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        msc.write_cache_entry("srv", "fp1", tools=[], utility_tools=[])
        assert msc.get_cached_entry("srv", "OTHER") is None
        assert not msc.has_cached_entry("srv", "OTHER")

    def test_missing_server_returns_none(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        assert msc.get_cached_entry("nope", "fp") is None

    def test_clear_cache_entry(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        msc.write_cache_entry("srv", "fp1", tools=[], utility_tools=[])
        msc.clear_cache_entry("srv")
        assert msc.get_cached_entry("srv", "fp1") is None

    def test_corrupt_cache_file_is_tolerated(self, monkeypatch, tmp_path):
        self._isolate(monkeypatch, tmp_path)
        (tmp_path / "cache.json").write_text("{not json", encoding="utf-8")
        assert msc.get_cached_entry("srv", "fp") is None
        # And writes recover the file.
        msc.write_cache_entry("srv", "fp", tools=[], utility_tools=[])
        assert msc.has_cached_entry("srv", "fp")

    def test_malformed_entry_shapes_are_tolerated(self):
        assert msc.tools_from_cache_entry({"tools": "nope"}) == []
        assert msc.utility_tools_from_cache_entry({}) == []


class TestCacheFileLocation:
    def test_cache_lives_under_hermes_home_cache_dir_with_0600(
        self, monkeypatch, tmp_path
    ):
        # Real path (no _cache_path monkeypatch): HERMES_HOME/cache/…, 0o600,
        # matching the discovery-cache precedent in tools/registry.py.
        import hermes_constants

        monkeypatch.setattr(hermes_constants, "get_hermes_home", lambda: tmp_path)
        path = msc._cache_path()
        assert path == tmp_path / "cache" / "mcp_schema_cache.json"
        msc.write_cache_entry("srv", "fp", tools=[], utility_tools=[])
        assert path.exists()
        assert (path.stat().st_mode & 0o777) == 0o600


class TestWriteSkip:
    def test_identical_payload_skips_rewrite(self, monkeypatch, tmp_path):
        monkeypatch.setattr(msc, "_cache_path", lambda: tmp_path / "cache.json")
        saves = []
        real_save = msc._save_all

        def _counting_save(data):
            saves.append(1)
            real_save(data)

        monkeypatch.setattr(msc, "_save_all", _counting_save)
        tools = [{"name": "t1", "description": "d", "inputSchema": {}}]
        msc.write_cache_entry("srv", "fp1", tools=tools, utility_tools=[])
        assert len(saves) == 1
        # Identical payload (reconnect / list_changed refresh) → no rewrite.
        msc.write_cache_entry("srv", "fp1", tools=list(tools), utility_tools=[])
        assert len(saves) == 1
        # Changed payload → rewrite.
        msc.write_cache_entry("srv", "fp2", tools=tools, utility_tools=[])
        assert len(saves) == 2


class TestWriteThroughPreservesSchema:
    """The live SDK-to-cache path must retain required tool parameters."""

    _SCHEMA = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "model": {"type": "string"},
        },
        "required": ["query", "model"],
    }

    def _cache_write_through(self, tmp_path, monkeypatch):
        import json
        from unittest.mock import MagicMock, patch

        from mcp.types import Tool

        import tools.mcp_tool as mt
        from tools.registry import ToolRegistry

        monkeypatch.setattr(msc, "_cache_path", lambda: tmp_path / "cache.json")
        # Live registration records per-server state in module globals. Keep
        # this probe isolated so it cannot affect later discovery assertions.
        for attr in (
            "_lazy_server_tool_names",
            "_lazy_server_configs",
            "_lazy_server_fingerprints",
            "_mcp_tool_server_names",
            "_server_trust_levels",
            "_tool_read_only_hints",
        ):
            monkeypatch.setattr(mt, attr, {})

        server = mt.MCPServerTask("probe_srv")
        server._tools = [
            Tool(name="zhida", description="probe", inputSchema=self._SCHEMA)
        ]
        server.session = MagicMock()

        with patch("tools.registry.registry", ToolRegistry()):
            registered = mt._register_server_tools("probe_srv", server, {})

        assert registered, "tool was not registered; write-through never ran"
        return json.loads(
            (tmp_path / "cache.json").read_text(encoding="utf-8")
        )["probe_srv"]

    def test_cached_schema_keeps_properties(self, tmp_path, monkeypatch):
        cached = self._cache_write_through(tmp_path, monkeypatch)["tools"][0][
            "inputSchema"
        ]
        assert set(cached.get("properties", {})) == {"query", "model"}

    def test_cached_schema_keeps_required(self, tmp_path, monkeypatch):
        cached = self._cache_write_through(tmp_path, monkeypatch)["tools"][0][
            "inputSchema"
        ]
        assert cached.get("required") == ["query", "model"]

    def test_cache_round_trip_reaches_agent_schema(self, tmp_path, monkeypatch):
        from unittest.mock import patch

        import tools.mcp_tool as mt
        from tools.registry import ToolRegistry

        entry = self._cache_write_through(tmp_path, monkeypatch)
        lazy_registry = ToolRegistry()
        with patch("tools.registry.registry", lazy_registry):
            names = mt._register_from_cache_sync("probe_srv", {}, entry)

        assert names, "lazy registration produced no tools"
        schema = lazy_registry.get_schema("mcp__probe_srv__zhida")
        assert schema is not None
        assert set(schema["parameters"].get("properties", {})) == {
            "query",
            "model",
        }
        assert schema["parameters"].get("required") == ["query", "model"]
