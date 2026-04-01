# Create or update a desktop shortcut to start Hermes stack (Gateway, Hypura GGUF, OAI proxy, TUI, FastAPI, ngrok, ...).
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\create-hermes-desktop-shortcut.ps1

param(
    [string]$ShortcutName = "Hermes Hypura Stack",
    [string]$IconPath = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$StartScript = Join-Path $ScriptDir "start-hermes-stack.ps1"

if (-not (Test-Path -LiteralPath $StartScript)) {
    Write-Error "Not found: $StartScript"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "$ShortcutName.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($lnkPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.Description = "Hermes: Gateway, Hypura GGUF inference, OpenAI proxy (8090), TUI, FastAPI, ngrok, VOICEVOX. Set HERMES_HYPURA_GGUF to override model path."
if ($IconPath -and (Test-Path -LiteralPath $IconPath)) {
    $Shortcut.IconLocation = $IconPath
} else {
    $Shortcut.IconLocation = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe,0"
}
$Shortcut.WindowStyle = 1
$Shortcut.Save()

Write-Host "Shortcut created: $lnkPath"
Write-Host "Target: $($Shortcut.TargetPath) $($Shortcut.Arguments)"
