# Idempotent Hermes stack restart: gateway/harness/webui/dashboard.
# Pass -StartLlama only for rollback/recovery checks that need the local GGUF server.
param(
    [switch]$SkipTunnels,
    [switch]$StartLlama,
    [switch]$StartGoWatchdog,
    [int]$WaitModelsSeconds = 300
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    $PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
}
$SharedVenvPython = Join-Path $env:USERPROFILE ".hermes\hermes-agent\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe) -and (Test-Path -LiteralPath $SharedVenvPython)) {
    $PythonExe = $SharedVenvPython
}
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python runtime not found. Checked: $ProjectRoot\\.venv, $ProjectRoot\\venv, $SharedVenvPython"
}
$HermesHome = Join-Path $env:USERPROFILE ".hermes"

function Get-HermesDotEnvValue {
    param([string]$Key)
    $dotEnv = Join-Path $HermesHome ".env"
    if (-not (Test-Path -LiteralPath $dotEnv)) { return $null }
    foreach ($line in Get-Content -LiteralPath $dotEnv) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        $eq = $trimmed.IndexOf('=')
        if ($eq -lt 1) { continue }
        $name = $trimmed.Substring(0, $eq).Trim().Trim([char]0xFEFF)
        if ($name -ne $Key) { continue }
        $value = $trimmed.Substring($eq + 1).Trim().Trim('"').Trim("'")
        if ($value) { return $value }
    }
    return $null
}

$DesiredModel = Get-HermesDotEnvValue "HERMES_LLAMA_ALIAS"
if (-not $DesiredModel) { $DesiredModel = Get-HermesDotEnvValue "HERMES_LLAMA_MODEL" }
if (-not $DesiredModel) { $DesiredModel = "yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF:Q4_K_M" }
$TailscaleScript = Join-Path $env:LOCALAPPDATA "HermesWebUI\Update-HermesTailscaleServe.ps1"
$RepoTailscaleScript = Join-Path $PSScriptRoot "Update-HermesTailscaleServe.ps1"
$LlamaNgrokScript = Join-Path $env:LOCALAPPDATA "HermesWebUI\Start-HermesLlamaNgrok.ps1"
$LineNgrokScript = Join-Path $env:LOCALAPPDATA "HermesWebUI\Start-HermesLineNgrok.ps1"
$WebUiScript = Join-Path $env:LOCALAPPDATA "HermesWebUI\Start-HermesWebUI.ps1"
$MemoryGraphScript = Join-Path $PSScriptRoot "start-obsidian-memory-graph-server.ps1"

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Test-SamePath([string]$Left, [string]$Right) {
    if ([string]::IsNullOrWhiteSpace($Left) -or [string]::IsNullOrWhiteSpace($Right)) { return $false }
    try {
        return [System.IO.Path]::GetFullPath($Left).TrimEnd('\') -ieq [System.IO.Path]::GetFullPath($Right).TrimEnd('\')
    } catch {
        return $false
    }
}

function Test-PathUnder([string]$Candidate, [string]$Root) {
    if ([string]::IsNullOrWhiteSpace($Candidate) -or [string]::IsNullOrWhiteSpace($Root)) { return $false }
    try {
        $fullCandidate = [System.IO.Path]::GetFullPath($Candidate)
        $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
        return $fullCandidate.StartsWith($fullRoot, [StringComparison]::OrdinalIgnoreCase)
    } catch {
        return $false
    }
}

function Stop-OwnedDesktop {
    $desktopExe = Join-Path $ProjectRoot "apps\desktop\release\win-unpacked\Hermes.exe"
    foreach ($candidate in @(Get-CimInstance Win32_Process -Filter "Name='Hermes.exe'" -ErrorAction SilentlyContinue)) {
        if (-not (Test-SamePath ([string]$candidate.ExecutablePath) $desktopExe)) {
            Write-Step ("Preserving foreign Hermes.exe PID {0}: executable path is not the configured Desktop" -f $candidate.ProcessId)
            continue
        }
        $current = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f [int]$candidate.ProcessId) -ErrorAction SilentlyContinue
        if (-not $current -or -not (Test-SamePath ([string]$current.ExecutablePath) $desktopExe) -or $current.CreationDate -ne $candidate.CreationDate) {
            Write-Warning ("Desktop PID {0} changed identity; refusing to stop it" -f $candidate.ProcessId)
            continue
        }
        Stop-Process -Id ([int]$candidate.ProcessId) -Force -ErrorAction Stop
    }
}

function Stop-PortListener {
    param([int]$Port, [string]$NamePattern = ".*")
    $ownerPid = 0
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($conn) { $ownerPid = [int]$conn.OwningProcess }
    }
    catch {
        Write-Step ("Get-NetTCPConnection failed for port {0}; using netstat fallback" -f $Port)
    }

    if ($ownerPid -le 0) {
        try {
            foreach ($line in (& netstat.exe -ano -p tcp 2>$null)) {
                if ($line -notmatch 'LISTENING') { continue }
                if ($line -notmatch (":{0}\s+" -f $Port)) { continue }
                $parts = ($line -split '\s+') | Where-Object { $_ }
                $candidate = 0
                if ([int]::TryParse($parts[-1], [ref]$candidate) -and $candidate -gt 0) {
                    $ownerPid = $candidate
                    break
                }
            }
        }
        catch {}
    }

    if ($ownerPid -le 0) { return }
    $candidate = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $ownerPid) -ErrorAction SilentlyContinue
    if (-not $candidate -or -not $candidate.ExecutablePath -or -not $candidate.CommandLine) { return }
    if ([string]$candidate.CommandLine -notmatch $NamePattern) {
        Write-Warning ("Port {0} PID {1} command does not match the expected service; preserving it" -f $Port, $ownerPid)
        return
    }
    $allowedRoots = @($ProjectRoot, $HermesHome, $PSScriptRoot, (Join-Path $env:LOCALAPPDATA "HermesWebUI"))
    if (-not ($allowedRoots | Where-Object { Test-PathUnder ([string]$candidate.ExecutablePath) $_ } | Select-Object -First 1)) {
        Write-Warning ("Port {0} PID {1} is outside configured stack roots; preserving it" -f $Port, $ownerPid)
        return
    }
    $current = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $ownerPid) -ErrorAction SilentlyContinue
    if (-not $current -or $current.CreationDate -ne $candidate.CreationDate -or -not (Test-SamePath ([string]$current.ExecutablePath) ([string]$candidate.ExecutablePath))) {
        Write-Warning ("Port {0} PID {1} changed identity; refusing to stop it" -f $Port, $ownerPid)
        return
    }
    Write-Step "Stopping owned listener on port $Port pid=$ownerPid"
    Stop-Process -Id $ownerPid -Force -ErrorAction Stop
    Start-Sleep -Seconds 2
}

function Stop-DesktopWatchdogStack {
    Write-Step "Stopping Desktop/watchdog processes (prevent Hermes.exe proliferation)"
    $launcher = Join-Path $PSScriptRoot "Start-HermesGoWatchdog.ps1"
    if (-not (Test-Path -LiteralPath $launcher)) { throw "Go watchdog lifecycle launcher is missing: $launcher" }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher -HermesRoot $ProjectRoot -HermesHome $HermesHome -Stop
    if ($LASTEXITCODE -ne 0) { throw "Go watchdog refused the stop request (exit $LASTEXITCODE)" }
    Stop-OwnedDesktop
    Start-Sleep -Seconds 2
}

Set-Location -LiteralPath $ProjectRoot
$env:HERMES_HOME = $HermesHome
$env:HF_HUB_CACHE = if ($env:HF_HUB_CACHE) { $env:HF_HUB_CACHE } else { "H:\elt_data\hf-cache" }

Write-Step "Stopping Hermes services (gateway/harness/webui/dashboard)"
Stop-DesktopWatchdogStack
try { & $PythonExe -m hermes_cli.main gateway stop --all 2>$null } catch {}
try { & $PythonExe -m hermes_cli.main harness stop 2>$null } catch {}
Stop-PortListener -Port 8787 -NamePattern "server\.py|hermes"
Stop-PortListener -Port 9120 -NamePattern "hermes_cli\.main dashboard|dashboard"
if ($StartLlama) {
    Stop-PortListener -Port 8080 -NamePattern "llama-server"
} else {
    Write-Step "Skipping llama restart; pass -StartLlama only for rollback/recovery checks"
}

if ($StartLlama) {
    $hotswapScript = Join-Path $PSScriptRoot "start-llama-hotswap.ps1"
    if (Test-Path -LiteralPath $hotswapScript) {
        Write-Step "Starting llama hot-swap router on :8080 (primary + Huihui agentic Q4_K_M)"
        $runtimePreset = Join-Path $HermesHome "llama\models-hotswap-primary-secondary.ini"
        if (Test-Path -LiteralPath $runtimePreset) {
            & $hotswapScript -RuntimePresetPath $runtimePreset -WaitSeconds $WaitModelsSeconds
        } else {
            & $hotswapScript -WaitSeconds $WaitModelsSeconds
        }
    } else {
        Write-Step "Starting llama secretary on :8080 (H: HF cache)"
        & (Join-Path $PSScriptRoot "start-llama-secretary.ps1") -WaitSeconds $WaitModelsSeconds
    }

    $modelsOk = $false
    $deadline = (Get-Date).AddSeconds($WaitModelsSeconds)
    $SecondaryModelId = "Huihui-gemma-4-12B-agentic-fable5-Q4_K_M"
    while ((Get-Date) -lt $deadline) {
        try {
            $models = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/models" -TimeoutSec 8
            $ids = @($models.data | ForEach-Object { $_.id })
            Write-Step ("8080 models: {0}" -f ($ids -join ", "))
            $hasPrimary = ($ids -contains $DesiredModel)
            $hasSecondary = ($ids -contains $SecondaryModelId)
            if ($hasPrimary -or ($ids.Count -gt 0 -and (Test-Path -LiteralPath $hotswapScript))) {
                # Router lists presets before/while primary loads; accept either listed id.
                if ($hasPrimary -or $hasSecondary -or $ids.Count -ge 1) {
                    $modelsOk = $true
                    break
                }
            }
            if ($ids.Count -gt 0) {
                Write-Warning "Desired model not listed yet; continuing to wait"
            }
        } catch {
            Write-Step ("Waiting for llama /v1/models: {0}" -f $_.Exception.Message)
        }
        Start-Sleep -Seconds 5
    }
    if (-not $modelsOk) {
        throw "llama /v1/models did not expose $DesiredModel within ${WaitModelsSeconds}s"
    }
}

if (-not $SkipTunnels) {
    if (Test-Path -LiteralPath $MemoryGraphScript) {
        Write-Step "Ensuring Obsidian memory-graph server (:8765)"
        & $MemoryGraphScript
    }

    if (Test-Path -LiteralPath $RepoTailscaleScript) {
        Copy-Item -LiteralPath $RepoTailscaleScript -Destination $TailscaleScript -Force
    }

    if (Test-Path -LiteralPath $TailscaleScript) {
        Write-Step "Updating Tailscale serve (/ /line /v1 /memory-graph)"
        if ($StartLlama) {
            & $TailscaleScript -LlamaPort 8080
        } else {
            & $TailscaleScript
        }
    } else {
        Write-Warning "Missing Tailscale script: $TailscaleScript"
    }

    if (Test-Path -LiteralPath $LineNgrokScript) {
        Write-Step "Ensuring LINE ngrok (:8646)"
        & $LineNgrokScript
    }
    if ($StartLlama -and (Test-Path -LiteralPath $LlamaNgrokScript)) {
        Write-Step "Ensuring llama ngrok (:8080)"
        & $LlamaNgrokScript -LlamaPort 8080
    }
}

Write-Step "Starting gateway"
& (Join-Path $PSScriptRoot "start-hermes-gateway.ps1") -StartLlama:$StartLlama

Write-Step "Starting harness"
Start-Process -FilePath $PythonExe -ArgumentList @("-m", "hermes_cli.main", "harness", "start") -WorkingDirectory $ProjectRoot -WindowStyle Hidden | Out-Null
Start-Sleep -Seconds 4

if (Test-Path -LiteralPath $WebUiScript) {
    Write-Step "Starting WebUI"
    & $WebUiScript
}
& (Join-Path $PSScriptRoot "start-hermes-dashboard.ps1") -HermesRoot $ProjectRoot -HermesHome $HermesHome

if ($StartGoWatchdog) {
    $GoWd = Join-Path $PSScriptRoot "Start-HermesGoWatchdog.ps1"
    $GoExe = Join-Path $PSScriptRoot "watchdog-go\dist\hermes-watchdog.exe"
    if (Test-Path -LiteralPath $GoWd) {
        Write-Step "Starting Go Desktop/backend watchdog (operator-only)"
        # Prefer an existing exe — never block the stack restart on go mod tidy/test.
        # If missing, BuildIfMissing is time-bounded inside Start-HermesGoWatchdog.ps1.
        $goArgs = @{
            HermesRoot = $ProjectRoot
            HermesHome = $HermesHome
            ForceRestart = $true
            BuildTimeoutSec = 180
        }
        if (-not (Test-Path -LiteralPath $GoExe)) {
            Write-Step "Go watchdog exe missing - bounded BuildIfMissing (SkipTest, 180s)"
            $goArgs.BuildIfMissing = $true
        } else {
            Write-Step "Using existing Go watchdog exe (skip rebuild)"
        }
        & $GoWd @goArgs
    } else {
        Write-Warning "Missing Go watchdog script: $GoWd"
    }
}

Write-Step "Health checks"
& $PythonExe -m hermes_cli.main gateway status
& $PythonExe -m hermes_cli.main harness status
Invoke-RestMethod http://127.0.0.1:8787/health -TimeoutSec 10 | Out-Null
# Dashboard can lag behind Start-Process; retry instead of failing the whole stack.
$dashOk = $false
foreach ($i in 1..12) {
    try {
        $code = (Invoke-WebRequest http://127.0.0.1:9120/ -UseBasicParsing -TimeoutSec 5).StatusCode
        if ($code -ge 200 -and $code -lt 500) { $dashOk = $true; break }
    } catch {
        Write-Step ("Waiting for dashboard :9120 (attempt $i/12)")
        Start-Sleep -Seconds 5
    }
}
if (-not $dashOk) {
    Write-Warning "Dashboard :9120 not ready after retries; gateway/llama/watchdog may still be healthy"
}
Write-Step "Hermes stack restart complete"
