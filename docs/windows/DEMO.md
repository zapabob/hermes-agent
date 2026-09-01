# Reproducible Windows demonstration

`scripts/demo/windows-demo.ps1` uses a dedicated `HERMES_HOME`, installation
directory, watchdog state directory, and non-production ports. It never reads
or copies the operator's normal profile secrets, model paths, prompts, or
sessions. Its default root is a fresh GUID-named temporary directory; an
explicit `-DemoRoot` must not already exist.

## Safe identity and installation run

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  scripts\demo\windows-demo.ps1 `
  -InstallerPath .\Hermes-Agent-Windows-0.21.0-x64-Setup.exe `
  -DemoRoot "$env:TEMP\HermesWindowsWorkstationDemo"
```

This verifies the dedicated clean installation, `hermes --version`, packaged
Desktop launch, local llama endpoint, embedded distribution identity, clean
build stamp, exact downstream commit, and frozen upstream identity. If the
local endpoint is not running, the report remains failed.

## Conversation and recovery run

Start the local model first, close every non-demo `Hermes.exe`, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  scripts\demo\windows-demo.ps1 `
  -InstallerPath .\Hermes-Agent-Windows-0.21.0-x64-Setup.exe `
  -ModelId local-model `
  -RunConversation `
  -ExerciseRecovery
```

Recovery mode refuses to proceed while another Hermes Desktop is running. It
also refuses pre-existing listeners on its dedicated watchdog or backend port.
It starts a dedicated Go watchdog, waits for its managed backend, terminates only
the backend PID reported by that watchdog, observes a different healthy PID,
and verifies that the demo session remains listed. It stops only the processes
it started and leaves the demo directory for inspection.

## 60 to 120 second recording shot list

1. Show the downstream release page, tag, SHA-256 file, and unsigned/signed manifest field.
2. Run the installer into the dedicated demo directory.
3. Show `hermes --version` with downstream and frozen upstream identities.
4. Launch the packaged Desktop and send the short local-model prompt.
5. Show llama and watchdog health on loopback.
6. Run recovery mode and show the reported backend PID change.
7. Show the same demo session after recovery.
8. End on `windows-demo.json` and the exact candidate SHA.

The script does not upload recordings or post to social platforms.
