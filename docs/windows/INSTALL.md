# Install Hermes Agent Windows Workstation Edition

This guide covers the unofficial downstream distribution in
`zapabob/hermes-agent-windows`. It does not install or represent the official
Nous Research distribution.

## Supported target

The qualified release target is Windows 11 x64 running native PowerShell,
Python, Node, and Electron. WSL is not required and is not used as evidence for
the Windows qualification gates. A consumer NVIDIA GPU is recommended for the
local llama.cpp and embedding features, but the Desktop can use remote model
providers without one.

## Recommended installer

Qualified builds are published on the
[Windows downstream Releases page](https://github.com/zapabob/hermes-agent-windows/releases).
Download the `Hermes-Agent-Windows-<version>-x64-Setup.exe`,
`release-manifest.json`, and `SHA256SUMS.txt` files from the same release.
Confirm the digest before running the installer:

```powershell
Get-FileHash .\Hermes-Agent-Windows-0.21.0-x64-Setup.exe -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

The current `0.21.0` candidate is intentionally represented as unsigned
unless `release-manifest.json` records `installer_signed: true`. Windows
SmartScreen or endpoint protection may therefore request confirmation. Check
the exact SHA-256 value and GitHub provenance before proceeding. Do not disable
antivirus globally.

The NSIS installer is per-user, does not require elevation, and lets the user
choose the destination. The usual default is under
`%LOCALAPPDATA%\Programs`; the chosen directory is authoritative. Profile data
remains separate under the active `HERMES_HOME`.

## Portable archive

Download `Hermes-Agent-Windows-<version>-x64-portable.zip`, verify its hash,
and extract it into a user-writable directory. The archive supports paths with
spaces and does not require a developer checkout. Start `Hermes.exe` from the
extracted directory. Move the complete directory when relocating the portable
installation.

## First launch

Start Hermes from the Start menu, the installer shortcut, or the extracted
portable directory. Complete provider setup in the Desktop. Secrets belong in
the profile-scoped secret store or `.env`; ordinary settings belong in
`config.yaml`. Do not place API keys in the repository.

Local llama.cpp/GGUF configuration is described in
[local-secretary-runtime.md](../local-secretary-runtime.md). Watchdog-managed
Desktop backend and embedding recovery are described in
[watchdog-go/README.md](../../scripts/windows/watchdog-go/README.md).

## Source and development install

Git, PowerShell, and `uv` are required for a source checkout. Node.js is also
required when building Desktop locally.

```powershell
git clone https://github.com/zapabob/hermes-agent-windows.git
Set-Location hermes-agent-windows
uv sync --locked --all-extras
uv run hermes --version
uv run hermes setup
```

For Desktop development:

```powershell
npm ci
npm --workspace apps/desktop run typecheck
npm --workspace apps/desktop run build
```

Source installation follows downstream `main`. Reproducible release installs
use the exact release tag and commit recorded in `release-manifest.json`.
