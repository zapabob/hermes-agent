# Retarget Desktop Hermes shortcuts to the Documents/source checkout.
# Packaged %LOCALAPPDATA%\...\Hermes.exe ignores Documents pulls and keeps
# Client at cNNNN — this .lnk launches start-hermes-desktop.ps1 instead.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\Retarget-HermesDesktopShortcut.ps1
#   powershell ... -File scripts\windows\Retarget-HermesDesktopShortcut.ps1 -RepoRoot "D:\src\hermes-agent"

param(
    [string]$RepoRoot = "C:\Users\downl\Documents\New project\hermes-agent",
    [string]$HermesHome = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $RepoRoot)) {
    throw "RepoRoot not found: $RepoRoot"
}

$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$StartScript = Join-Path $RepoRoot "scripts\windows\start-hermes-desktop.ps1"
if (-not (Test-Path -LiteralPath $StartScript)) {
    throw "Missing start script: $StartScript"
}

. (Join-Path $RepoRoot "scripts\windows\Resolve-CanonicalHermesHome.ps1")
$HermesHome = Resolve-CanonicalHermesHome -Preferred $HermesHome -RepoRoot $RepoRoot

$psExe = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$args = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$StartScript`" -HermesRoot `"$RepoRoot`" -Cwd `"$RepoRoot`" -HermesHome `"$HermesHome`""

$icon = Join-Path $RepoRoot "apps\desktop\assets\icon.ico"
if (-not (Test-Path -LiteralPath $icon)) {
    $icon = Join-Path $RepoRoot "apps\desktop\release\win-unpacked\resources\icon.ico"
}
if (-not (Test-Path -LiteralPath $icon)) {
    $icon = Join-Path $RepoRoot "apps\desktop\release\win-unpacked\Hermes.exe"
}
$iconLoc = if (Test-Path -LiteralPath $icon) { "$icon,0" } else { "$psExe,0" }

$userDesktop = [Environment]::GetFolderPath("Desktop")
$userPrograms = [Environment]::GetFolderPath("Programs")
$taskbarPins = Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
$folder = Join-Path $userDesktop "Hermes Agent"
New-Item -ItemType Directory -Path $folder -Force | Out-Null

$targets = @(
    (Join-Path $userDesktop "Hermes.lnk"),
    (Join-Path $userDesktop "Hermes Desktop.lnk"),
    (Join-Path $folder "Hermes Desktop.lnk"),
    (Join-Path $folder "Hermes.lnk"),
    (Join-Path $userPrograms "Hermes.lnk")
)

# Windows groups the running Desktop by com.nousresearch.hermes. A legacy
# Electron dev shortcut with that AppUserModelID can therefore supply the
# taskbar icon even though Hermes.exe itself is correctly stamped. Retarget only
# aliases that already exist; do not create new legacy names or alter unrelated
# Electron installations.
$existingAliases = @(
    (Join-Path $userPrograms "Electron.lnk"),
    (Join-Path $userPrograms "Hermes (2).lnk"),
    (Join-Path $taskbarPins "Electron.lnk"),
    (Join-Path $taskbarPins "Hermes.lnk"),
    (Join-Path $taskbarPins "Hermes Desktop.lnk")
)
foreach ($alias in $existingAliases) {
    if (Test-Path -LiteralPath $alias) {
        $targets += $alias
    }
}
$targets = @($targets | Select-Object -Unique)

# Kill stale packaged Desktop so the next launch is the retargeted one.
Get-Process Hermes, electron -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

$Wsh = New-Object -ComObject WScript.Shell
$written = @()
foreach ($lnk in $targets) {
    $sc = $Wsh.CreateShortcut($lnk)
    $sc.TargetPath = $psExe
    $sc.Arguments = $args
    $sc.WorkingDirectory = $RepoRoot
    $sc.Description = "Hermes Desktop → source ($RepoRoot)"
    $sc.WindowStyle = 7
    $sc.IconLocation = $iconLoc
    $sc.Save()
    $written += $lnk
    Write-Host "Wrote $lnk"
    Write-Host "  -> $psExe"
    Write-Host "  $args"
}

# Ask Explorer to repaint shortcut icons without deleting icon-cache files or
# restarting the shell. This is best-effort because some Windows SKUs do not
# ship ie4uinit.exe.
$iconRefresh = Join-Path $env:SystemRoot "System32\ie4uinit.exe"
if (Test-Path -LiteralPath $iconRefresh) {
    try {
        & $iconRefresh -show 2>$null
    }
    catch {
        Write-Warning "Could not refresh the Windows icon cache: $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "Done. Double-click Desktop\Hermes.lnk (or Hermes Agent\Hermes Desktop.lnk)." -ForegroundColor Green
Write-Host "Update root is now Documents; Client cNNNN should clear after restart." -ForegroundColor DarkGray
$written
