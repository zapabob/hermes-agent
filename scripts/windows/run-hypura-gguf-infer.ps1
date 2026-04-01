# Hypura one-shot inference with a local GGUF (UTF-8 prompt file recommended).
# Usage (from repo root):
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/run-hypura-gguf-infer.ps1
#
# Override:
#   $env:HYPURA_EXE = "C:\path\to\hypura.exe"
#   $env:GGUF_PATH = "C:\path\to\model.gguf"
#   $env:PROMPT_FILE = "C:\path\to\prompt_utf8.txt"

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$hypura = if ($env:HYPURA_EXE -and (Test-Path -LiteralPath $env:HYPURA_EXE.Trim())) {
    $env:HYPURA_EXE.Trim()
} else {
    "C:\Users\downl\Desktop\hypura-main\hypura-main\target_release_rtx\release\hypura.exe"
}

$gguf = if ($env:GGUF_PATH -and (Test-Path -LiteralPath $env:GGUF_PATH.Trim())) {
    $env:GGUF_PATH.Trim()
} else {
    "C:\Users\downl\Desktop\EasyNovelAssistant\EasyNovelAssistant\KoboldCpp\Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"
}

$promptFile = if ($env:PROMPT_FILE -and (Test-Path -LiteralPath $env:PROMPT_FILE.Trim())) {
    $env:PROMPT_FILE.Trim()
} else {
    Join-Path $RepoRoot "_tmp_llama_prompt.txt"
}

if (-not (Test-Path -LiteralPath $hypura)) { Write-Error "hypura.exe not found: $hypura" }
if (-not (Test-Path -LiteralPath $gguf)) { Write-Error "GGUF not found: $gguf" }
if (-not (Test-Path -LiteralPath $promptFile)) { Write-Error "Prompt file not found: $promptFile" }

$prompt = (Get-Content -LiteralPath $promptFile -Raw -Encoding utf8).Trim()
$maxTok = if ($env:HYPURA_MAX_TOKENS) { [int]$env:HYPURA_MAX_TOKENS } else { 96 }

Write-Host "hypura: $hypura"
Write-Host "gguf:   $gguf"
Write-Host "prompt: $promptFile ($maxTok tokens max)"
& $hypura run $gguf --prompt $prompt --max-tokens $maxTok
