# Register / unregister Hermes Full Stack logon autostart via Windows Task Scheduler.
# Automatically starts Qwen3.8-27B llama-server, Go Watchdog, Hermes Gateway, WebUI, and Desktop at logon.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Register-HermesFullAutostart.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Register-HermesFullAutostart.ps1 -Unregister
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Register-HermesFullAutostart.ps1 -SkipLlama

[CmdletBinding()]
param(
    [switch]$Unregister,
    [switch]$SkipLlama,
    [switch]$SkipWebUI,
    [switch]$SkipGoWatchdog,
    [switch]$SkipDesktop,
    [int]$StartupDelaySeconds = 15,
    [string]$TaskName = "HermesFullStackAutoStart"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$FullStackScript = Join-Path $ScriptDir "Start-HermesFullStack.ps1"
$LogonAccount = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$StaleScheduledTaskNames = @(
    "HermesFullStackAutoStart",
    "HermesGatewayAutoStart",
    "HermesAgentStackAutoStart",
    "HermesLlamaFallbackRTX3060",
    "HermesLlamaFallbackRTX3080",
    "HermesLlamaFallbackRTX3060Watchdog"
)

function Unregister-HermesTask {
    param([string]$Name)
    $existing = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false
        return $true
    }
    return $false
}

if ($Unregister) {
    Write-Host "Unregistering Hermes autostart tasks..." -ForegroundColor Cyan
    $removed = @()
    foreach ($t in $StaleScheduledTaskNames) {
        if (Unregister-HermesTask -Name $t) {
            $removed += $t
        }
    }
    Write-Host "Removed tasks: $(if ($removed) { $removed -join ', ' } else { '(none)' })" -ForegroundColor Green
    exit 0
}

# Clean stale legacy tasks to avoid duplicate resource consumption
foreach ($t in $StaleScheduledTaskNames) {
    Unregister-HermesTask -Name $t | Out-Null
}

$flags = @()
if ($SkipLlama) { $flags += "-SkipLlama" }
if ($SkipWebUI) { $flags += "-SkipWebUI" }
if ($SkipGoWatchdog) { $flags += "-SkipGoWatchdog" }
if ($SkipDesktop) { $flags += "-SkipDesktop" }
if ($StartupDelaySeconds -gt 0) { $flags += "-StartupDelaySeconds $StartupDelaySeconds" }

$flagString = if ($flags.Count -gt 0) { " " + ($flags -join " ") } else { "" }
$psCommand = "& '$FullStackScript'$flagString"
$argumentList = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"$psCommand`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argumentList -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $LogonAccount
if ($StartupDelaySeconds -gt 0) {
    $trigger.Delay = "PT${StartupDelaySeconds}S"
}

$principal = New-ScheduledTaskPrincipal -UserId $LogonAccount -LogonType Interactive -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Full Hermes Stack (Qwen3.8-27B llama, Go Watchdog, WebUI, Gateway, Desktop) at logon" `
    -Force | Out-Null

Write-Host "Successfully registered Scheduled Task: $TaskName" -ForegroundColor Green
Write-Host "  Trigger: At Logon (User: $LogonAccount, Delay: ${StartupDelaySeconds}s)"
Write-Host "  Script:  $FullStackScript $flagString"
Write-Host ""
Write-Host "To unregister:" -ForegroundColor Yellow
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`" -Unregister"
