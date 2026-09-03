# Carry-surface metrics, 2026-08-26

Frozen upstream: 5a8e8a6b87487c0e0785cd9eb561cc6a96c64f5e

| Metric | Value |
| --- | ---: |
| All fork-specific LOC | 758526 |
| Upstream-owned fork LOC | 358669 |
| Fork-owned LOC | 399857 |
| UTR | 0.472850 |
| Carry Surface | 2645 files |
| CWC | 3156839 |

LOC is added plus deleted lines relative to the frozen upstream tree.
Generated metric reports are excluded to avoid self-referential totals.
Coupling is 3 for CARRY.yaml paths, 2 for other runtime/source paths,
and 1 for tests, docs, workflows, and generated documentation.

## Highest CWC paths

| Path | Frequency | Patch | Coupling | CWC |
| --- | ---: | ---: | ---: | ---: |
| gateway/run.py | 60 | 2414 | 2 | 289680 |
| hermes_state.py | 50 | 2271 | 2 | 227100 |
| plugins/platforms/buzz/adapter.py | 43 | 2284 | 2 | 196424 |
| tui_gateway/server.py | 41 | 2175 | 2 | 178350 |
| hermes_cli/web_server.py | 32 | 2477 | 2 | 158528 |
| tests/gateway/test_buzz_adapter.py | 35 | 3621 | 1 | 126735 |
| cli.py | 16 | 3782 | 2 | 121024 |
| apps/desktop/electron/main.ts | 34 | 962 | 3 | 98124 |
| agent/auxiliary_client.py | 23 | 2069 | 2 | 95174 |
| cron/scheduler.py | 26 | 1477 | 2 | 76804 |
| agent/conversation_loop.py | 25 | 1245 | 2 | 62250 |
| agent/conversation_compression.py | 34 | 553 | 2 | 37604 |
| agent/context_compressor.py | 24 | 769 | 2 | 36912 |
| tests/test_tui_gateway_server.py | 13 | 2586 | 1 | 33618 |
| tools/browser_tool.py | 20 | 723 | 2 | 28920 |
| hermes_cli/main.py | 23 | 579 | 2 | 26634 |
| gateway/platforms/api_server.py | 7 | 1857 | 2 | 25998 |
| hermes_cli/config_defaults.py | 34 | 352 | 2 | 23936 |
| hermes_cli/config.py | 17 | 664 | 2 | 22576 |
| agent/agent_init.py | 13 | 517 | 3 | 20163 |
| gateway/hosted_rooms.py | 4 | 2446 | 2 | 19568 |
| apps/desktop/src/plugins/hermes-bots/i18n.ts | 8 | 1086 | 2 | 17376 |
| cron/jobs.py | 18 | 478 | 2 | 17208 |
| uv.lock | 5 | 1612 | 2 | 16120 |
| hermes_cli/models.py | 23 | 345 | 2 | 15870 |

This is a coupling report, not a target to improve by relocating code
without reducing its actual dependency on upstream behavior.
