# OpenManus x Qwen3.8 harness — one-command bring-up.
# 1. starts (or reuses) the local llama-server serving qwen3.8-27b-abliterated-mtp
# 2. verifies /health and a real chat completion
# 3. verifies the Hermes openmanus plugin resolves the local LLM
param(
    [int]$Port = 8080,
    [switch]$SkipLlama,
    [switch]$CpuMoe,
    [switch]$Probe,
    [int]$MaxSteps = 6
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Test-LlamaHealth {
    param([int]$Port)
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 5
        return ($r.status -eq "ok")
    } catch { return $false }
}

Write-Host "== step 1: llama-server ==" -ForegroundColor Cyan
if (Test-LlamaHealth -Port $Port) {
    Write-Host "already healthy on port $Port" -ForegroundColor Green
} elseif ($SkipLlama) {
    throw "llama-server is not healthy on port $Port and -SkipLlama was passed"
} else {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass `
        -File (Join-Path $PSScriptRoot "start-llama-qwen38-openmanus.ps1") -Port $Port -CpuMoe:$CpuMoe
    if (-not (Test-LlamaHealth -Port $Port)) { throw "llama-server failed to become healthy" }
}

Write-Host "`n== step 2: real completion ==" -ForegroundColor Cyan
$body = @{
    model       = "qwen3.8-27b-abliterated-mtp"
    messages    = @(@{ role = "user"; content = "Reply with exactly: READY" })
    max_tokens  = 256
    temperature = 0
} | ConvertTo-Json -Depth 5

$resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/v1/chat/completions" `
    -Method Post -ContentType "application/json" -Body $body -TimeoutSec 300
$content = $resp.choices[0].message.content
Write-Host "content = '$content'" -ForegroundColor Green
if (-not $content) { throw "empty completion content — model is not answering" }

Write-Host "`n== step 3: openmanus plugin config ==" -ForegroundColor Cyan
& py -3 (Join-Path $RepoRoot "scripts\standalone\openmanus_qwen38_check.py")
if ($LASTEXITCODE -ne 0) { throw "openmanus config check failed" }

if ($Probe) {
    Write-Host "`n== step 4: live agent probe ==" -ForegroundColor Cyan
    & py -3 (Join-Path $RepoRoot "scripts\standalone\openmanus_qwen38_probe.py") $MaxSteps 1800
    if ($LASTEXITCODE -ne 0) { throw "live probe failed" }
}

Write-Host "`nHARNESS READY" -ForegroundColor Green
