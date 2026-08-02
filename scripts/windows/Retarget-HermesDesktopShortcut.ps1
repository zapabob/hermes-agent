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

$icon = Join-Path $RepoRoot ".venv\Scripts\hermes.exe"
if (-not (Test-Path -LiteralPath $icon)) {
    $icon = Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\apps\desktop\release\win-unpacked\Hermes.exe"
}
$iconLoc = if (Test-Path -LiteralPath $icon) { "$icon,0" } else { "$psExe,0" }

$userDesktop = [Environment]::GetFolderPath("Desktop")
$folder = Join-Path $userDesktop "Hermes Agent"
New-Item -ItemType Directory -Path $folder -Force | Out-Null

$targets = @(
    (Join-Path $userDesktop "Hermes.lnk"),
    (Join-Path $userDesktop "Hermes Desktop.lnk"),
    (Join-Path $folder "Hermes Desktop.lnk"),
    (Join-Path $folder "Hermes.lnk")
)

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

Write-Host ""
Write-Host "Done. Double-click Desktop\Hermes.lnk (or Hermes Agent\Hermes Desktop.lnk)." -ForegroundColor Green
Write-Host "Update root is now Documents; Client cNNNN should clear after restart." -ForegroundColor DarkGray
$written
