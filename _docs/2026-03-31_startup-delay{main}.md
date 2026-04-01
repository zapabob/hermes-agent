# Hermes Startup Delay Stabilization Log

- DateTime (from MCP `hex_to_datetime`): 2026-03-31T15:41:05+00:00
- Scope: Add startup delay to improve network initialization stability on Windows auto start.

## Changes

1. Updated:
   - `scripts/windows/start-hermes-gateway.ps1`

2. Added startup delay behavior:
   - Default delay: `30` seconds
   - Optional override: `HERMES_STARTUP_DELAY_SECONDS`
   - Validation:
     - Uses override only when it is a non-negative integer.
     - Falls back to `30` if invalid or unset.

3. Launch flow:
   - Checks whether gateway is already running.
   - If not running, waits configured delay.
   - Starts `py -3 -m hermes_cli.main gateway run` in background.

## Verification

- Smoke test command:
  - Set `HERMES_STARTUP_DELAY_SECONDS=1`
  - Run `start-hermes-gateway.ps1`
- Result:
  - Script exited successfully.
  - Delay path executed and no launch failure observed.
