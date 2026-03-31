param(
    [string]$TaskName = "HermesAgentGatewayAutoStart"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartScript = Resolve-Path (Join-Path $ScriptDir "start-hermes-gateway.ps1")

$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
$registered = $false

try {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Description "Auto start Hermes gateway at logon" `
        -Force | Out-Null
    $registered = $true
} catch {
    Write-Warning "Task Scheduler registration failed: $($_.Exception.Message)"
}

if ($registered) {
    Write-Host "Registered task: $TaskName"
    Write-Host "Action: powershell.exe $actionArgs"
    exit 0
}

# Fallback: Startup folder launcher.
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
New-Item -ItemType Directory -Path $startupDir -Force | Out-Null
$startupCmd = Join-Path $startupDir "HermesAgentGatewayAutoStart.cmd"
@(
    "@echo off"
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
) | Set-Content -Path $startupCmd -Encoding ASCII

Write-Host "Created startup launcher: $startupCmd"
