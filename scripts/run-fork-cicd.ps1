# Fork Original 6-Core Parallel CI/CD PowerShell Entrypoint
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  HERMES FORK PARALLEL CI/CD (6-Core / 12-Thread Orchestration)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

$CiScript = Join-Path $ScriptDir "run_cicd_parallel.py"

& $PythonExe $CiScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] CI/CD verification failed!" -ForegroundColor Red
    exit $LASTEXITCODE
} else {
    Write-Host "`n[SUCCESS] ALL FORK CI/CD CHECKS PASSED (ALL GREEN)!" -ForegroundColor Green
    exit 0
}
