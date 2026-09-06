# Compatibility shim for installations whose scheduled task still references
# the former PowerShell watchdog. The Go watchdog is the only outer automatic
# restart authority; this script may bootstrap it, but never probes, kills, or
# restarts Desktop/backend processes itself.

[CmdletBinding()]
param(
    [int]$IntervalSec = 20,
    [int]$FailThreshold = 2,
    [int]$StartupGraceSec = 45,
    [int]$ManagedBackendPort = 9119,
    [switch]$Once,
    [string]$HermesRoot = "",
    [string]$HermesHome = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRootCandidate = if ($HermesRoot) { $HermesRoot } else { Join-Path $ScriptDir "..\.." }
$RepoRoot = (Resolve-Path -LiteralPath $RepoRootCandidate -ErrorAction Stop).Path
if (-not $HermesHome) { $HermesHome = Join-Path $env:USERPROFILE ".hermes" }

$LogDir = Join-Path $HermesHome "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir "desktop-backend-watchdog.log"

function Write-WdLog([string]$Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

$GoLauncher = Join-Path $ScriptDir "Start-HermesGoWatchdog.ps1"
if (-not (Test-Path -LiteralPath $GoLauncher)) {
    throw "Go watchdog launcher is missing: $GoLauncher"
}

$launcherArgs = @{
    IntervalSec        = $IntervalSec
    FailThreshold      = $FailThreshold
    ManagedBackendPort = $ManagedBackendPort
    HermesRoot         = $RepoRoot
    HermesHome         = $HermesHome
    BuildIfMissing     = $true
}
if ($Once) { $launcherArgs.Once = $true }

Write-WdLog "legacy PowerShell watchdog delegated to the sole Go watchdog authority"
& $GoLauncher @launcherArgs
