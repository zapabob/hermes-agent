# Zapabob Hermes Fork — Layout Guide

This directory documents how **this repository** differs from
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).
It does **not** replace upstream code. Official Hermes stays in the repo root
(`run_agent.py`, `hermes_cli/`, `gateway/`, `apps/`, …). Fork-only behaviour
lives at the edges: plugins, merge overlays, Windows ops scripts, and local
operator automation.

## Identity — Generic Agent Harness

This repository is a **generic AI agent harness** and **Windows universal AI workstation base**.
`NousResearch/hermes-agent` is upstream only — fetched until its development stalls or stops.
There is **zero runtime dependency** on Nous infrastructure. See
[`harness/GENERIC_HARNESS.md`](harness/GENERIC_HARNESS.md) and
[`_docs/2026-09-03_generic-harness-independence.md`](../_docs/2026-09-03_generic-harness-independence.md).

## Directory map

| Path | Purpose |
|------|---------|
| [`harness/`](harness/README.md) | Upstream merge policy, overlays, and sync entry points (`scripts/merge_tools/`) |
| [`harness/GENERIC_HARNESS.md`](harness/GENERIC_HARNESS.md) | Generic harness definition & growth roadmap |
| [`extensions/`](extensions/README.md) | Fork-owned plugins, core tool deltas, and optional skills |
| [`operations/`](operations/README.md) | Windows stack scripts, cron helpers, Tailscale/ngrok, daily automation |
| [`local-workspace/`](local-workspace/README.md) | Root scratch policy + `notes/` for tracked operator drafts |
| [`harness/upstream-development-guide.md`](harness/upstream-development-guide.md) | Full upstream-aligned AGENTS-style development guide |

## Rules for contributors and agents

1. **Upstream is authoritative** for the agent core, gateway loop, and security fixes.
2. **Never delete** harness files under `scripts/merge_tools/` or vendor pins used by evolution tools.
3. **Prefer plugins + skills** over editing `run_agent.py` / `model_tools.py` when adding capability.
4. **Do not commit** build output, logs, media scratch, secrets, or `_docs/` implementation logs.
5. Read [`AGENTS.md`](AGENTS.md) before changing fork-specific areas.

## Quick commands

```powershell
# Policy dry-run before merging upstream
py -3 scripts\sync_all.py --dry-run --allow-preflight-blockers

# Restart Hermes stack (llama excluded by default)
powershell -ExecutionPolicy Bypass -File scripts\windows\restart-hermes-stack.ps1

# Desktop rebuild
py -3 -m hermes_cli.main desktop --build-only --force-build
```

## Related docs

- Root [`README.md`](../README.md) — fork feature summary for humans
- Root [`AGENTS.md`](../AGENTS.md) — short agent entrypoint (fork + learned prefs)
- [`harness/upstream-development-guide.md`](harness/upstream-development-guide.md) — long-form core guide
- **[Fork-specific features (for AI agents)](harness/upstream-development-guide.md#fork-specific-features-for-ai-agents)** — catalog of self_evolution, fork tools/plugins, vendor submodules, Windows ops, merge tooling, Desktop/watchdog notes, peripheral MCP/memory integrations
