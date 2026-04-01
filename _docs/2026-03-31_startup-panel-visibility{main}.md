# Hermes Startup Panel Visibility Log

- DateTime (from MCP `hex_to_datetime`): 2026-03-31T15:45:40+00:00
- Scope: Show Hermes gateway window at startup instead of hidden launch.

## Changes

1. Updated:
   - `scripts/windows/start-hermes-gateway.ps1`

2. Startup window behavior:
   - Default window style changed to `Normal` (visible at startup).
   - Added env override: `HERMES_GATEWAY_WINDOW_STYLE`
   - Supported values: `Normal`, `Minimized`, `Maximized`, `Hidden`
   - Invalid values are ignored and default remains `Normal`.

3. Existing behavior preserved:
   - Duplicate-start guard (`is_gateway_running`) remains active.
   - Delay logic (`HERMES_STARTUP_DELAY_SECONDS`) remains active.
   - Log redirection to `~/.hermes/logs` remains active.

## Verification

- Smoke test:
  - Set `HERMES_STARTUP_DELAY_SECONDS=0`
  - Execute startup script
- Result:
  - Script exits successfully with updated window behavior.
