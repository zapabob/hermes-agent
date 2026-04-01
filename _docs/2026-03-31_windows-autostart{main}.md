# Hermes Windows AutoStart Implementation Log

- DateTime (from MCP `hex_to_datetime`): 2026-03-31T15:39:23+00:00
- Scope: Enable Hermes-Agent automatic startup on Windows power-on/login path.

## Changes

1. Added startup launcher script:
   - `scripts/windows/start-hermes-gateway.ps1`
   - Behavior:
     - Resolves repository root dynamically.
     - Uses `HERMES_HOME` or defaults to `~/.hermes`.
     - Creates log directory `~/.hermes/logs`.
     - Checks existing gateway process via `gateway.status.is_gateway_running()`.
     - Starts `py -3 -m hermes_cli.main gateway run` only when not already running.

2. Added registration script:
   - `scripts/windows/register-hermes-autostart.ps1`
   - Behavior:
     - Attempts Task Scheduler registration (`AtLogOn`).
     - On permission failure, automatically falls back to Startup folder launcher creation.

3. Applied fallback autostart in this environment:
   - Created:
     - `C:\Users\downl\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\HermesAgentGatewayAutoStart.cmd`
   - This ensures Hermes gateway starts automatically at user logon after power-on.

## Verification

- Executed startup script manually:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/start-hermes-gateway.ps1`
- Confirmed gateway status:
  - `py -3 -m hermes_cli.main gateway status`
  - Result: Gateway running (PID detected).

## Notes

- `hermes gateway install` remains unsupported on this Windows environment.
- Startup folder fallback is now active and requires no elevated privileges.
