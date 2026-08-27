# Carry-surface metrics, 2026-08-26

Frozen upstream: 5fc308a70719a83cccdbba4c0e39c23f5a8239d5

| Metric | Value |
| --- | ---: |
| All fork-specific LOC | 477401 |
| Upstream-owned fork LOC | 156585 |
| Fork-owned LOC | 320816 |
| UTR | 0.327995 |
| Carry Surface | 1323 files |
| CWC | 435356 |

LOC is added plus deleted lines relative to the frozen upstream tree.
Generated metric reports are excluded to avoid self-referential totals.
Coupling is 3 for CARRY.yaml paths, 2 for other runtime/source paths,
and 1 for tests, docs, workflows, and generated documentation.

## Highest CWC paths

| Path | Frequency | Patch | Coupling | CWC |
| --- | ---: | ---: | ---: | ---: |
| hermes_cli/update_cmd.py | 19 | 1450 | 2 | 55100 |
| apps/desktop/electron/main.ts | 20 | 865 | 3 | 51900 |
| hermes_cli/web_server.py | 15 | 1631 | 2 | 48930 |
| apps/desktop/src/plugins/hermes-bots/plugin.js | 18 | 902 | 2 | 32472 |
| tui_gateway/server.py | 10 | 812 | 2 | 16240 |
| plugins/platforms/slack/adapter.py | 10 | 507 | 2 | 10140 |
| hermes_cli/main.py | 11 | 387 | 2 | 8514 |
| apps/desktop/src/app/contrib/hooks/use-background-sync.test.ts | 8 | 461 | 2 | 7376 |
| tests/gateway/test_slack.py | 6 | 1205 | 1 | 7230 |
| tools/browser_tool.py | 11 | 287 | 2 | 6314 |
| apps/desktop/src/app/session/hooks/profile-rail-fresh-chat-owner.test.tsx | 4 | 779 | 2 | 6232 |
| scripts/desktop-update/windows.ps1 | 6 | 462 | 2 | 5544 |
| gateway/run.py | 7 | 378 | 2 | 5292 |
| hermes_cli/models.py | 9 | 291 | 2 | 5238 |
| apps/desktop/src/store/gateway.ts | 9 | 278 | 2 | 5004 |
| apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts | 12 | 198 | 2 | 4752 |
| apps/desktop/src/app/contrib/hooks/use-background-sync.ts | 8 | 270 | 2 | 4320 |
| hermes_cli/config.py | 6 | 351 | 2 | 4212 |
| agent/conversation_loop.py | 2 | 1051 | 2 | 4204 |
| cron/scheduler.py | 4 | 499 | 2 | 3992 |
| apps/desktop/electron/remote-lifecycle.test.ts | 7 | 228 | 2 | 3192 |
| tools/terminal_tool.py | 2 | 517 | 3 | 3102 |
| package-lock.json | 1 | 1546 | 2 | 3092 |
| hermes_cli/browser_connect.py | 12 | 125 | 2 | 3000 |
| uv.lock | 1 | 1475 | 2 | 2950 |

This is a coupling report, not a target to improve by relocating code
without reducing its actual dependency on upstream behavior.
