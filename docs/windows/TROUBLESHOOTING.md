# Windows troubleshooting

Use the exact downstream version, commit, and frozen upstream SHA from
`hermes --version` and `release-manifest.json` when reporting a problem. Never
include API keys, model paths, usernames, prompts, or private session content.

## Locked executable during update

Close Hermes and allow the Desktop/backend processes to exit. If the Go
watchdog is active, stop it through the operator-controlled process or its
authenticated stop API before retrying. Do not widen process termination to
unrelated Python, Node, or Electron processes.

## Antivirus or SmartScreen warning

The `0.20.5-win.1` candidate is unsigned unless its manifest says otherwise.
Verify the SHA-256 hash and GitHub provenance, then submit a false-positive
sample to the security vendor when appropriate. Do not disable real-time
protection globally and do not add a broad drive exclusion.

## Hermes is already running

Use Task Manager to confirm whether the existing `Hermes.exe` belongs to the
intended installation. Close that instance before opening a second portable or
installed copy. The E2E scripts terminate only the process tree they started.

## Port collision

Common workstation endpoints include Desktop backend `9119`, watchdog `9920`,
llama `8080`, and embeddings `8082`. Inspect listener ownership before changing
configuration:

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -In 8080,8082,9119,9920
```

Preserve unknown listeners. Change the Hermes setting or stop the confirmed
owner rather than terminating a process based only on a port number.

## Local llama is unavailable

```powershell
Invoke-RestMethod http://127.0.0.1:8080/v1/models -TimeoutSec 5
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\check-local-llm.ps1
```

Confirm the configured model exists without publishing its local path. Review
`docs/local-secretary-runtime.md` for provider and port settings.

## Watchdog status

```powershell
Invoke-RestMethod http://127.0.0.1:9920/health -TimeoutSec 5
Invoke-RestMethod http://127.0.0.1:9920/api/status -TimeoutSec 5
```

The watchdog is an external operator process. It is not a Hermes plugin, tool,
skill, MCP server, or agent-reachable restart authority.

## Desktop and backend version skew

Check `hermes --version`, the packaged executable version fields, and the
running gateway or backend status separately. Restarting Desktop does not prove
that a detached gateway changed versions. Reinstall the exact downstream build
and restart each applicable supervisor through its documented route.

## Bounded recovery

Use `scripts/windows/restart-hermes-stack.ps1` only after reviewing its target
paths and options. For release evidence, run the dedicated demo or qualification
script rather than modifying the primary profile. A physical reboot remains
unverified until observed after the machine returns.
