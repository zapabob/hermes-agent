---
name: hermes-plugin-integration
description: "Integrate external tools as Hermes plugins."
version: 0.1.0
author: zapabob, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [plugin, integration, conventions]
    related_skills: [hermes-agent-skill-authoring, test-driven-development]
---

# Hermes Plugin Integration

## Overview

Integrate external tools and libraries as Hermes Agent plugins following the repo's established conventions. This skill covers the pattern for making third-party tools (like LMCache) work within Hermes's plugin system.

## When to Use

- **User asks** to integrate an external tool/library as a Hermes plugin
- **Adding a new capability** that fits the plugin system rather than as a core tool
- **Converting** an existing script or tool to Hermes plugin format
- **Following the footprint ladder** — prefer plugin over core tool when capability is niche or local

## Core Patterns

### 1. Plugin Directory Structure

Plugins live under `plugins/` in the hermes-agent repo or `~/.hermes/plugins/`. A minimal plugin needs:

```
plugins/my-plugin/
├── __init__.py       # Plugin registration
├── plugin.yaml       # Plugin metadata (if dashboard plugin)
└── your_module.py    # Main plugin logic
```

### 2. Plugin Storage Convention (from `plugins/plugin_storage.py`)

Use `plugins/plugin_storage.py` for durable plugin state:

```python
from plugins.plugin_storage import plugin_data_dir, plugin_db

state_file = plugin_data_dir("my-plugin") / "state.json"
conn = plugin_db("my-plugin")  # Lives at <hermes_home>/plugin-data/my-plugin/data.db
```

**Key:** Data directory survives plugin update/remove at `<hermes_home>/plugin-data/<name>/`

### 3. Plugin Registration

Follow existing plugin patterns (e.g., `hermes-achievements`, `hermes-bot-mode`):
- Register via `__init__.py`
- Mount at appropriate API endpoints
- Follow dashboard plugin conventions if UI-facing

### 4. Following the Footprint Ladder

Prefer these rungs in order:

1. **Extend existing code** — variation of existing plugin
2. **CLI command + skill** — manage config/state via `hermes <subcommand>`
3. **Service-gated tool (`check_fn`)** — appears only when prerequisite configured
4. **Plugin** — third-party/niche capability not in core
5. **MCP server** — if needs structured I/O but not core-fundamental
6. **New core tool** — only when fundamental and broadly useful

## Example: LMCache Integration

LMCache (https://github.com/zapabob/LMCache.git) is a KV cache management engine. As a plugin:

- **Not integrated by default** — remains independent project
- **Can be invoked** via `execute_code` or custom skills
- **Plugin path would be:** `plugins/lmcache/` with proper `__init__.py`
- **Storage** via `plugin_data_dir("lmcache")` for any cached state

## Pitfalls

- **⚠️ Not a core tool** — LMCache has its own AGENTS.md, pyproject.toml, CI
- **⚠️ Storage survives updates** — use `plugin_data_dir()`, not `plugins/<name>/`
- **⚠️ Git remote already exists** — `lmcache` remote configured but project standalone
- **⚠️ Plugin vs integration** — some tools are better as standalone invocable tools

## Verification

After integration:

```bash
# Check plugin is discoverable
hermes plugins list

# Verify storage path
hermes --config show plugin-data-dir

# Test basic import
python -c "from plugins import discover_plugins; discover_plugins()"
```

## Related Skills

- `hermes-agent-skill-authoring` — author SKILL.md files in-repo
- `test-driven-development` — write tests before integration code
- `software-development/plan` — plan multi-step integration workflow
