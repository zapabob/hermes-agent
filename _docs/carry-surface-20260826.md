# Carry-surface metrics, 2026-08-26

Frozen upstream: 1fe0f2f3ac9748ce799272eb93bee2937b5ab802

| Metric | Value |
| --- | ---: |
| All fork-specific LOC | 434684 |
| Upstream-owned fork LOC | 118852 |
| Fork-owned LOC | 315832 |
| UTR | 0.273422 |
| Carry Surface | 965 files |
| CWC | 156111 |

LOC is added plus deleted lines relative to the frozen upstream tree.
Generated metric reports are excluded to avoid self-referential totals.
Coupling is 3 for CARRY.yaml paths, 2 for other runtime/source paths,
and 1 for tests, docs, workflows, and generated documentation.

## Highest CWC paths

| Path | Frequency | Patch | Coupling | CWC |
| --- | ---: | ---: | ---: | ---: |
| apps/desktop/electron/main.ts | 33 | 572 | 3 | 56628 |
| cli.py | 3 | 2868 | 2 | 17208 |
| hermes_cli/web_server.py | 4 | 1372 | 2 | 10976 |
| hermes_cli/main.py | 14 | 296 | 2 | 8288 |
| tools/terminal_tool.py | 5 | 435 | 3 | 6525 |
| gateway/run.py | 13 | 168 | 2 | 4368 |
| agent/auxiliary_client.py | 2 | 1048 | 2 | 4192 |
| agent/agent_init.py | 4 | 317 | 3 | 3804 |
| hermes_cli/config_defaults.py | 12 | 157 | 2 | 3768 |
| uv.lock | 1 | 1473 | 2 | 2946 |
| tests/test_tui_gateway_server.py | 1 | 1903 | 1 | 1903 |
| cron/scheduler.py | 4 | 236 | 2 | 1888 |
| hermes_cli/auth.py | 1 | 895 | 2 | 1790 |
| apps/desktop/src/store/gateway.ts | 14 | 61 | 2 | 1708 |
| apps/desktop/src/plugins/hermes-bots/plugin.js | 9 | 85 | 2 | 1530 |
| apps/desktop/src/i18n/en.ts | 8 | 92 | 2 | 1472 |
| apps/desktop/src/i18n/zh.ts | 8 | 92 | 2 | 1472 |
| tui_gateway/server.py | 2 | 356 | 2 | 1424 |
| apps/desktop/src/global.d.ts | 9 | 72 | 2 | 1296 |
| apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts | 19 | 34 | 2 | 1292 |
| apps/desktop/src/i18n/ja.ts | 7 | 91 | 2 | 1274 |
| agent/memory_manager.py | 4 | 138 | 2 | 1104 |
| hermes_cli/tools_config.py | 8 | 65 | 2 | 1040 |
| apps/desktop/src/i18n/types.ts | 6 | 85 | 2 | 1020 |
| hermes_cli/doctor.py | 6 | 85 | 2 | 1020 |

This is a coupling report, not a target to improve by relocating code
without reducing its actual dependency on upstream behavior.
