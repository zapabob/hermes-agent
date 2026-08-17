param(
    [string]$HermesRoot = "",
    [string]$Cwd = "",
    [string]$HermesHome = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
. (Join-Path $ScriptDir "Resolve-CanonicalHermesHome.ps1")

if (-not $HermesRoot) {
    $HermesRoot = $RepoRoot
}
if (-not $Cwd) {
    $Cwd = $HermesRoot
}
$HermesHome = Resolve-CanonicalHermesHome -Preferred $HermesHome -RepoRoot $RepoRoot

$PythonExe = Join-Path $HermesRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    $PythonExe = Join-Path $HermesRoot "venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $PythonExe)) {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}

$env:HERMES_HOME = $HermesHome
$env:HERMES_DESKTOP_HERMES_ROOT = $HermesRoot
$env:HERMES_DESKTOP_CWD = $Cwd
$WebDist = Join-Path $HermesRoot "hermes_cli\web_dist"
if (Test-Path -LiteralPath (Join-Path $WebDist "index.html")) {
    $env:HERMES_DESKTOP_DASHBOARD_WEB_DIST = $WebDist
}
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$staleDesktopPattern = [regex]::Escape("AppData\Local\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe")
$staleDesktopProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -and $_.CommandLine -match $staleDesktopPattern
}
foreach ($proc in $staleDesktopProcesses) {
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

# Resolve packaged EXE (LOCALAPPDATA install takes priority over repo release dir).
$PackagedExe = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe"
if (-not (Test-Path -LiteralPath $PackagedExe)) {
    $PackagedExe = Join-Path $HermesRoot "apps\desktop\release\win-unpacked\Hermes.exe"
}

# Guard: skip if a packaged Hermes.exe is already running from the resolved path.
$packagedRunning = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -and $_.CommandLine -match [regex]::Escape($PackagedExe)
} | Select-Object -First 1
if ($packagedRunning) {
    Write-Host "[start-hermes-desktop] Packaged Hermes.exe already running (pid=$($packagedRunning.ProcessId)) — skipping launch."
    exit 0
}


# Refuse worktree roots — User/agent mistakes keep relaunching .worktrees\* with --skip-build.
$normalizedRoot = [System.IO.Path]::GetFullPath($HermesRoot)
if ($normalizedRoot -match '(?i)[\\/]\.worktrees[\\/]') {
    throw "Refusing Hermes Desktop launch from worktree: $normalizedRoot`nUse canonical repo: C:\Users\downl\Documents\New project\hermes-agent"
}
Set-Location -LiteralPath $HermesRoot

# Launch packaged Hermes.exe — never use --source or node_modules/electron.
# If the EXE is missing, build first: hermes desktop --build-only --force-build
if (-not (Test-Path -LiteralPath $PackagedExe)) {
    throw (
        "Packaged Hermes.exe not found. Build it first:`n" +
        "  hermes desktop --build-only --force-build`n" +
        "Searched:`n" +
        "  $env:LOCALAPPDATA\hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe`n" +
        "  $HermesRoot\apps\desktop\release\win-unpacked\Hermes.exe"
    )
}

$WorkDir = Split-Path -Parent $PackagedExe
Write-Host "[start-hermes-desktop] Launching: $PackagedExe"
Write-Host "[start-hermes-desktop] HERMES_DESKTOP_HERMES_ROOT=$env:HERMES_DESKTOP_HERMES_ROOT"
Start-Process -FilePath $PackagedExe -WorkingDirectory $WorkDir
exit 0
