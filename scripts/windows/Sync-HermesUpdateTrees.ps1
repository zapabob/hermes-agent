# Sync Documents (dev) checkout and %LOCALAPPDATA%\hermes\hermes-agent (managed)
# to the same origin/<branch> tip, then optionally run `hermes update` + Desktop rebuild.
#
# Usage (PowerShell):
#   .\scripts\windows\Sync-HermesUpdateTrees.ps1
#   .\scripts\windows\Sync-HermesUpdateTrees.ps1 -RebuildDesktop
#   .\scripts\windows\Sync-HermesUpdateTrees.ps1 -DocsRoot "D:\src\hermes-agent"
#
# Why: Desktop update checks often hit the managed tree while you edit Documents.
# When those SHAs diverge, Client stays at v0.x (cNNNN) even after a Documents pull.

param(
    [string]$DocsRoot = "C:\Users\downl\Documents\New project\hermes-agent",
    [string]$ManagedRoot = "",
    [string]$Branch = "main",
    [switch]$RebuildDesktop,
    [switch]$SkipHermesUpdate,
    [switch]$SkipStopProcesses
)

$ErrorActionPreference = "Stop"

if (-not $ManagedRoot) {
    if (-not $env:LOCALAPPDATA) {
        throw "LOCALAPPDATA is empty — run this on native Windows PowerShell."
    }
    $ManagedRoot = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent"
}

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Assert-GitCheckout([string]$Path) {
    if (-not (Test-Path -LiteralPath (Join-Path $Path ".git"))) {
        throw "Not a git checkout: $Path"
    }
}

function Get-ShortSha([string]$Path) {
    Push-Location -LiteralPath $Path
    try {
        return (git rev-parse --short HEAD).Trim()
    } finally {
        Pop-Location
    }
}

function Stop-HermesLockHolders {
    Write-Step "Stopping Hermes / Electron processes that lock managed files"
    $names = @("Hermes", "electron", "hermes")
    foreach ($name in $names) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Step ("  stop pid={0} name={1}" -f $_.Id, $_.ProcessName)
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
}

function Sync-GitTree {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$BranchName
    )

    Assert-GitCheckout -Path $Path
    $before = Get-ShortSha -Path $Path
    Write-Step ("{0}: {1} @ {2}" -f $Label, $Path, $before)

    Push-Location -LiteralPath $Path
    try {
        git fetch --quiet origin
        $current = (git rev-parse --abbrev-ref HEAD).Trim()
        if ($current -ne $BranchName) {
            Write-Step ("  checkout {0} (was {1})" -f $BranchName, $current)
            git checkout $BranchName
        }
        git pull --ff-only origin $BranchName
        if ($LASTEXITCODE -ne 0) {
            throw ("git pull --ff-only failed in {0}. Resolve local commits/dirty state, then re-run." -f $Path)
        }
    } finally {
        Pop-Location
    }

    $after = Get-ShortSha -Path $Path
    Write-Step ("{0}: {1} -> {2}" -f $Label, $before, $after)
    return $after
}

Write-Step "=== Sync Hermes update trees (option B) ==="
Write-Step ("DocsRoot     = {0}" -f $DocsRoot)
Write-Step ("ManagedRoot  = {0}" -f $ManagedRoot)
Write-Step ("Branch       = {0}" -f $Branch)

if (-not (Test-Path -LiteralPath $DocsRoot)) {
    throw "DocsRoot not found: $DocsRoot"
}
if (-not (Test-Path -LiteralPath $ManagedRoot)) {
    throw "ManagedRoot not found: $ManagedRoot (install Hermes first, or pass -ManagedRoot)"
}

if (-not $SkipStopProcesses) {
    Stop-HermesLockHolders
}

$docsSha = Sync-GitTree -Label "Documents" -Path $DocsRoot -BranchName $Branch
$managedSha = Sync-GitTree -Label "LOCALAPPDATA" -Path $ManagedRoot -BranchName $Branch

if (-not $SkipHermesUpdate) {
    $hermesCmd = Get-Command hermes -ErrorAction SilentlyContinue
    if ($hermesCmd) {
        Write-Step "Running: hermes update"
        & hermes update
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "hermes update exited with code $LASTEXITCODE — check output above"
        }
    } else {
        Write-Warning "hermes not on PATH — skipped hermes update. Open a new shell after install, or run from managed venv."
    }
}

if ($RebuildDesktop) {
    $desktopDir = Join-Path $ManagedRoot "apps\desktop"
    if (-not (Test-Path -LiteralPath $desktopDir)) {
        throw "Desktop package missing: $desktopDir"
    }
    Write-Step "Rebuilding Desktop in managed tree"
    Push-Location -LiteralPath $ManagedRoot
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed at repo root" }
    } finally {
        Pop-Location
    }
    Push-Location -LiteralPath $desktopDir
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed in apps/desktop" }
    } finally {
        Pop-Location
    }
}

$docsFinal = Get-ShortSha -Path $DocsRoot
$managedFinal = Get-ShortSha -Path $ManagedRoot

Write-Host ""
Write-Step "=== Result ==="
Write-Host ("  Documents    : {0}" -f $docsFinal)
Write-Host ("  LOCALAPPDATA : {0}" -f $managedFinal)

if ($docsFinal -ne $managedFinal) {
    Write-Warning "SHAs still differ. Check remotes (origin URL) and local dirty commits."
    exit 2
}

Write-Step "Trees match. Retarget Desktop shortcuts to Documents (source launch)."
$retarget = Join-Path $PSScriptRoot "Retarget-HermesDesktopShortcut.ps1"
if (Test-Path -LiteralPath $retarget) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $retarget -RepoRoot $DocsRoot
}
else {
    Write-Warning "Retarget script missing — run scripts\windows\Retarget-HermesDesktopShortcut.ps1 after pull"
}
Write-Step "Restart via Desktop\Hermes.lnk (not the old LOCALAPPDATA Hermes.exe)."
exit 0
