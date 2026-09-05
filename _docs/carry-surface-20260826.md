# Carry-surface metrics, 2026-08-26

Frozen upstream: 5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e

| Metric | Value |
| --- | ---: |
| All fork-specific LOC | 724655 |
| Upstream-owned fork LOC | 316002 |
| Fork-owned LOC | 408653 |
| UTR | 0.436072 |
| Carry Surface | 2384 files |
| CWC | 2665964 |

LOC is added plus deleted lines relative to the frozen upstream tree.
Generated metric reports are excluded to avoid self-referential totals.
Coupling is 3 for CARRY.yaml paths, 2 for other runtime/source paths,
and 1 for tests, docs, workflows, and generated documentation.

## Highest CWC paths

| Path | Frequency | Patch | Coupling | CWC |
| --- | ---: | ---: | ---: | ---: |
| gateway/run.py | 60 | 1998 | 2 | 239760 |
| plugins/platforms/buzz/adapter.py | 43 | 2282 | 2 | 196252 |
| hermes_state.py | 50 | 1617 | 2 | 161700 |
| hermes_cli/web_server.py | 32 | 2129 | 2 | 136256 |
| tests/gateway/test_buzz_adapter.py | 35 | 3621 | 1 | 126735 |
| cli.py | 16 | 3782 | 2 | 121024 |
| tui_gateway/server.py | 41 | 1260 | 2 | 103320 |
| agent/auxiliary_client.py | 23 | 2058 | 2 | 94668 |
| hermes_cli/update_cmd.py | 46 | 965 | 2 | 88780 |
| agent/conversation_loop.py | 25 | 1234 | 2 | 61700 |
| cron/scheduler.py | 26 | 1075 | 2 | 55900 |
| agent/context_compressor.py | 24 | 740 | 2 | 35520 |
| tests/test_tui_gateway_server.py | 13 | 2506 | 1 | 32578 |
| gateway/platforms/api_server.py | 7 | 1853 | 2 | 25942 |
| hermes_cli/main.py | 23 | 517 | 2 | 23782 |
| apps/desktop/electron/main.ts | 34 | 221 | 3 | 22542 |
| agent/conversation_compression.py | 34 | 326 | 2 | 22168 |
| hermes_cli/config_defaults.py | 34 | 321 | 2 | 21828 |
| gateway/hosted_rooms.py | 4 | 2446 | 2 | 19568 |
| agent/agent_init.py | 13 | 498 | 3 | 19422 |
| hermes_cli/models.py | 23 | 409 | 2 | 18814 |
| tools/browser_tool.py | 20 | 458 | 2 | 18320 |
| apps/desktop/src/plugins/hermes-bots/i18n.ts | 8 | 1086 | 2 | 17376 |
| uv.lock | 5 | 1610 | 2 | 16100 |
| hermes_cli/config.py | 17 | 423 | 2 | 14382 |

This is a coupling report, not a target to improve by relocating code
without reducing its actual dependency on upstream behavior.
