# Real workstation qualification

GitHub-hosted Windows runners provide native CI evidence but no consumer GPU,
sleep/resume observation, or physical reboot. Real-workstation qualification is
therefore a separate report and must never be inferred from CI.

## Safety and privacy

The collector records Windows version/build, CPU architecture, NVIDIA model and
VRAM, downstream and upstream SHAs, packaged executable identity and hash,
aggregate Desktop process state and version identity, loopback health results,
and explicit manual power-cycle results. A passing Desktop result requires a
running executable whose embedded distribution identity matches the candidate.
It does not record usernames, executable paths, local model paths, command
lines, API keys, prompts, or private sessions.

## Procedure

Install the exact candidate, verify its hash, launch Desktop, and start the
configured backend, watchdog, llama, and embedding services. Confirm each
loopback endpoint locally. Then observe one sleep/resume cycle and one physical
restart/recovery cycle. Do not claim either result before the machine returns
and the relevant services are checked again.

Run the collector from the exact candidate checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  scripts\windows\Get-HermesWorkstationQualification.ps1 `
  -ArtifactPath .\Hermes-Agent-Windows-0.21.0-x64-Setup.exe `
  -SleepResumeResult passed `
  -RestartRecoveryResult passed `
  -OutputPath .\workstation-qualification.json
```

Use `-AllowIncomplete` only to inspect a partial local report; its overall
status remains `failed`. Feed a passed report into
`Test-HermesWindowsQualification.ps1 -Scope real_workstation` to produce the
combined qualification evidence.

The report is valid only for its recorded downstream commit and frozen upstream
SHA. Hardware results must not be reused for a different candidate SHA.
