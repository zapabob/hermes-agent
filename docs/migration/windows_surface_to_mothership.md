# Windows Surface to mothership migration runbook

This runbook moves the Hermes Windows runtime from a temporary Surface back to
the primary workstation after the workstation has recovered. It is intentionally
secret-safe by default: repository files can be committed, while `.env`,
`auth.json`, model files, and local logs stay outside git unless you explicitly
export them into a private migration bundle.

## Scope

Use this when the Surface has been used as the active Hermes host and the
mothership PC is ready to become the active host again.

The migration covers:

- the `hermes-agent` checkout
- the sibling `hermes-WebUI` checkout
- `C:\Users\<user>\.hermes\config.yaml`
- optional private secrets such as `.env` and `auth.json`
- Windows Scheduled Tasks for gateway, WebUI, Tailscale Serve, and watchdogs
- post-migration health checks for WebUI, gateway, Telegram, Tailscale, and
  optional llama fallback

## Safety rules

- Do not commit `.env`, `auth.json`, model files, generated migration bundles,
  or WebUI local state.
- Export secrets only with `-IncludeSecrets`, and only to a private transfer
  device or encrypted share.
- On import, secrets are not restored unless `-RestoreSecrets` is supplied.
- Use Tailscale Serve for phone access when firewall changes need admin rights.
- Prefer scheduled-task restarts or narrow PID targeting. Avoid broad Python
  process kills because WebUI, gateway, and helper processes overlap.

## 1. Prepare the Surface

Make sure the Surface has the latest fork state pushed:

```powershell
git -C "C:\Users\butte\OneDrive\ドキュメント\New project\hermes-agent" status --short --branch
git -C "C:\Users\butte\OneDrive\ドキュメント\New project\hermes-agent" push origin main
```

Create a secret-safe migration bundle:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\windows\export-hermes-host-migration.ps1
```

For a private handoff that includes `.env` and `auth.json`, use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\windows\export-hermes-host-migration.ps1 `
  -IncludeSecrets
```

The exporter writes a folder and zip under:

```text
C:\Users\<user>\.hermes\migration\
```

## 2. Prepare the mothership PC

Clone or update the repo:

```powershell
git clone https://github.com/zapabob/hermes-agent-windows.git "C:\Users\butte\OneDrive\ドキュメント\New project\hermes-agent"
cd "C:\Users\butte\OneDrive\ドキュメント\New project\hermes-agent"
git pull --ff-only origin main
```

Create the venv if needed:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\pip.exe install -e ".[all,dev]"
```

Place the `hermes-WebUI` checkout beside `hermes-agent` or pass `-WebUiRoot`
to the import script.

## 3. Import the bundle

Secret-safe import:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\windows\import-hermes-host-migration.ps1 `
  -MigrationPath "C:\path\to\hermes-host-YYYYMMDD-HHMMSS.zip" `
  -InstallAutostart
```

Trusted private import with secrets:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\windows\import-hermes-host-migration.ps1 `
  -MigrationPath "C:\path\to\hermes-host-YYYYMMDD-HHMMSS.zip" `
  -RestoreSecrets `
  -InstallAutostart `
  -StartAfterImport
```

The importer backs up existing destination files under:

```text
C:\Users\<user>\.hermes\migration\backup-before-import-*
```

## 4. Restore local-only dependencies

These are intentionally not in git and may need to be reinstalled on the
mothership PC:

- `C:\Users\<user>\.hermes\.env`
- `C:\Users\<user>\.hermes\auth.json`
- WebUI `.env`, if the WebUI checkout still depends on one
- llama fallback binary, normally
  `%LOCALAPPDATA%\Programs\llama-turboquant\bin\llama-server.exe`
- fallback GGUF model path referenced by `HERMES_LLAMA_MODEL_PATH`
- Tailscale login state
- browser/device auth for `openai-codex`, if runtime auth fails in practice

The llama fallback will not pass verification unless both
`HERMES_LLAMA_SERVER_EXE` or the default `llama-server.exe` path and
`HERMES_LLAMA_MODEL_PATH` exist.

## 5. Start and verify

Start the registered tasks:

```powershell
Start-ScheduledTask -TaskName HermesGatewayAutoStart
Start-ScheduledTask -TaskName HermesWebUIAutoStartNative
Start-ScheduledTask -TaskName HermesTailscaleServeWebUI
```

Run the health gate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\windows\verify-hermes-host-migration.ps1
```

Expected core results:

- `http://127.0.0.1:8787/` returns HTTP 200
- `http://127.0.0.1:8787/health` returns HTTP 200
- `http://127.0.0.1:8787/api/auth/status` reports password auth enabled
- `C:\Users\<user>\.hermes\gateway_state.json` reports `running`
- Telegram state is `connected`
- Tailscale Serve proxies the WebUI to `127.0.0.1:8787`

If llama fallback is intentionally absent, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts\windows\verify-hermes-host-migration.ps1 `
  -SkipLlama
```

Use `-RequireLlama` only after the fallback binary and model path have both
been restored.
