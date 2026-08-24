# Register / unregister Hermes Desktop logon autostart via Task Scheduler and Startup shortcut.
[CmdletBinding()]
param(
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$ExePath = Join-Path $RepoRoot "apps\desktop\release\win-unpacked\Hermes.exe"
$DesktopScript = Join-Path $ScriptDir "start-hermes-desktop.ps1"
$TaskName = "HermesDesktopAutoStart"
$StartupDir = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs\Startup')
$ShortcutPath = [System.IO.Path]::Combine($StartupDir, 'Hermes Desktop.lnk')

if ($Unregister) {
    # Remove Scheduled Task
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Unregistered scheduled task: $TaskName" -ForegroundColor Yellow
    }
    # Remove Startup Shortcut
    if (Test-Path -LiteralPath $ShortcutPath) {
        Remove-Item -LiteralPath $ShortcutPath -Force
        Write-Host "Removed startup shortcut: $ShortcutPath" -ForegroundColor Yellow
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Target Hermes.exe not found at: $ExePath`nPlease build desktop app first."
}
if (-not (Test-Path -LiteralPath $DesktopScript)) {
    throw "Desktop launcher script not found at: $DesktopScript"
}

# 1. Register Task Scheduler Task
$LogonAccount = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$HermesHome = Join-Path $env:USERPROFILE ".hermes"
$desktopCommand = "& '$DesktopScript' -HermesRoot '$RepoRoot' -Cwd '$RepoRoot' -HermesHome '$HermesHome'"
$actionArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command $desktopCommand"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $LogonAccount
$trigger.Delay = "PT15S"
$principal = New-ScheduledTaskPrincipal -UserId $LogonAccount -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Auto-start Hermes Desktop packaged app at logon" `
    -Force | Out-Null

Write-Host "Successfully registered Scheduled Task: $TaskName" -ForegroundColor Green

# 2. Create Startup Shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = $actionArgs
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.Description = "Hermes Desktop Application"
$Shortcut.Save()

Write-Host "Successfully created Startup shortcut: $ShortcutPath" -ForegroundColor Green
