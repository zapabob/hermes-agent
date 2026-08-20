# LMCache Plugin - Quick Start

## Installation

```bash
# The plugin is auto-discovered by Hermes Agent
# Ensure it's in the plugins directory
ls plugins/lmcache/
```

## Basic Usage

### Check LMCache Status
```python
# Via Hermes tools
result = hermes_tool("lmcache_status")
# or via the plugin directly
from plugins.lmcache import get_plugin
plugin = get_plugin()
status = plugin.get_status()
print(status)
```

### Set a Cache Entry
```python
# Set cache with key "model_config" and value "qwen3-32b"
result = hermes_tool("lmcache_set_entry", {
    "key": "model_config",
    "value": '{"model": "qwen3-32b", "temp": 0.7}',
    "ttl": 3600
})
print(result)
```

### Get a Cache Entry
```python
# Retrieve a cached entry
result = hermes_tool("lmcache_get_entry", {
    "key": "model_config"
})
print(result)
```

### Record Optimization Stats
```python
# Record performance metrics
result = hermes_tool("lmcache_record_optimization", {
    "model_name": "qwen3-32b",
    "context_length": 131072,
    "ttft_ms": 125.5,
    "throughput": 38.2
})
print(result)
```

### Get Optimization Stats
```python
# Retrieve stats for a specific model
result = hermes_tool("lmcache_get_optimization_stats", {
    "model_name": "qwen3-32b"
})
print(result)
```

## Data Storage

All data is stored durably at:
```
<hermes_home>/plugin-data/lmcache/data.db
```

This survives plugin updates and removals. You can inspect the SQLite database directly:

```bash
sqlite3 ~/.hermes/plugin-data/lmcache/data.db "SELECT * FROM cache_status;"
sqlite3 ~/.hermes/plugin-data/lmcache/data.db "SELECT * FROM optimization_stats;"
```

## Plugin Lifecycle

- **Install**: Plugin auto-registers on Hermes startup
- **Update**: `hermes plugins update lmcache` git-pulls, data preserved in plugin-data/
- **Remove**: `hermes plugins remove lmcache` removes tool access, data preserved in plugin-data/
- **Data persists**: User data in `<hermes_home>/plugin-data/lmcache/` is never deleted by plugin operations

## Development

### Adding New Tools

1. Add tool function following the pattern: `lmcache_<verb>_entry`, `lmcache_<verb>_stats`
2. Register in `register_tools(ctx)` function
3. Ensure handler returns JSON string
4. Add to `plugin.yaml` under `exposed_tools` if needed

### Testing

```bash
# Run plugin-specific tests if any
cd hermes-agent
python -m pytest tests/ -k "lmcache" -v

# Or test tools directly
python -c "from plugins.lmcache import lmcache_status; import json; print(json.loads(lmcache_status()))"
```

## Configuration

No configuration required for basic operation. To customize:

- Set `HERMES_HOME` env var to change data location
- Modify `plugin.yaml` for version/author info
- Add `requires_env` entries for any API keys needed