# One-shot: stop Hermes Desktop, rebuild from Documents source, retarget
# shortcuts, restart Desktop, and restart llama hot-swap (RTX 5060 Ti).
#
# Usage (PowerShell):
#   cd "C:\Users\downl\Documents\New project\hermes-agent"
#   git pull origin main
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Restart-HermesDesktopAndLlama.ps1
#   powershell ... -File scripts\windows\Restart-HermesDesktopAndLlama.ps1 -SkipLlama
#   powershell ... -File scripts\windows\Restart-HermesDesktopAndLlama.ps1 -SkipDesktopRebuild

param(
    [string]$RepoRoot = "C:\Users\downl\Documents\New project\hermes-agent",
    [switch]$SkipDesktopRebuild,
    [switch]$SkipLlama,
    [switch]$SkipRetarget,
    [switch]$SkipPull,
    [int]$LlamaWaitSeconds = 300
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message) -ForegroundColor Cyan
}

if (-not (Test-Path -LiteralPath $RepoRoot)) {
    throw "RepoRoot not found: $RepoRoot"
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

Write-Step "=== Hermes Desktop + llama hot-standby restart ==="
Write-Step "RepoRoot = $RepoRoot"

if (-not $SkipPull) {
    Write-Step "git pull origin main"
    Push-Location -LiteralPath $RepoRoot
    try {
        Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $RepoRoot ".git\index.lock")
        git fetch origin
        git checkout main
        git pull --ff-only origin main
        if ($LASTEXITCODE -ne 0) {
            throw "git pull --ff-only failed. Fix local commits/dirty state, then re-run."
        }
    } finally {
        Pop-Location
    }
}

Write-Step "Stopping Hermes / Electron / stale desktop"
Get-Process Hermes, electron, hermes -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Step ("  stop pid={0} name={1}" -f $_.Id, $_.ProcessName)
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

if (-not $SkipDesktopRebuild) {
    Write-Step "npm install (repo root) + apps/desktop build"
    Push-Location -LiteralPath $RepoRoot
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    } finally {
        Pop-Location
    }
    $desktop = Join-Path $RepoRoot "apps\desktop"
    Push-Location -LiteralPath $desktop
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
    } finally {
        Pop-Location
    }
}

if (-not $SkipRetarget) {
    $retarget = Join-Path $RepoRoot "scripts\windows\Retarget-HermesDesktopShortcut.ps1"
    if (Test-Path -LiteralPath $retarget) {
        Write-Step "Retarget Desktop shortcuts → Documents source"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $retarget -RepoRoot $RepoRoot
    } else {
        Write-Warning "Retarget script missing — pull main (#46) first"
    }
}

if (-not $SkipLlama) {
    $hotswap = Join-Path $RepoRoot "scripts\windows\start-llama-hotswap.ps1"
    if (-not (Test-Path -LiteralPath $hotswap)) {
        throw "Missing llama hot-swap script: $hotswap"
    }
    Write-Step "llama hot-swap -ForceRestart -WarmSecondary (WaitSeconds=$LlamaWaitSeconds)"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $hotswap -ForceRestart -WarmSecondary -WaitSeconds $LlamaWaitSeconds
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "llama hot-swap exited $LASTEXITCODE — check ~/.hermes/logs and GGUF paths"
    }
}

$startDesktop = Join-Path $RepoRoot "scripts\windows\start-hermes-desktop.ps1"
if (-not (Test-Path -LiteralPath $startDesktop)) {
    throw "Missing: $startDesktop"
}
Write-Step "Starting Hermes Desktop (source)"
Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$startDesktop`"",
        "-HermesRoot", "`"$RepoRoot`"",
        "-Cwd", "`"$RepoRoot`""
    ) `
    -WorkingDirectory $RepoRoot

Write-Step "Done."
Write-Host "  Desktop: use Desktop\Hermes.lnk (Documents source)" -ForegroundColor Green
Write-Host "  llama:   start-llama-hotswap.ps1 (primary + warm secondary)" -ForegroundColor Green
Write-Host "  SHA:     $(git -C $RepoRoot rev-parse --short HEAD)" -ForegroundColor DarkGray
exit 0
