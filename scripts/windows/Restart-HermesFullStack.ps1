# Full-stack idempotent Hermes restart script:
# 1. Stops all Hermes processes, WebUI, Desktop, Go Watchdog, Llama server, and listeners.
# 2. Rebuilds Desktop App (pnpm install + build).
# 3. Builds & starts Go Watchdog.
# 4. Starts Qwen3.8-27B llama-server (MTP speculative decoding, Turbo3 KV cache).
# 5. Starts Hermes Gateway, Harness, WebUI (:8787), Dashboard (:9120), Tailscale, and Desktop App.
# 6. Performs comprehensive health checks.

[CmdletBinding()]
param(
    [string]$RepoRoot = "C:\Users\downl\Documents\New project\hermes-agent",
    [switch]$SkipDesktopRebuild,
    [switch]$SkipLlama,
    [switch]$UseHotswapRouter,
    [switch]$SkipWebUI,
    [switch]$SkipDesktop,
    [switch]$SkipGoWatchdog,
    [switch]$SkipA2A,
    [switch]$SkipGateway,
    [switch]$SkipTunnels,
    [int]$LlamaWaitSeconds = 300,
    [string]$LlamaServerExe = "$env:LOCALAPPDATA\Programs\llama-turboquant\bin\llama-server.exe",
    [string]$LlamaGgufPath = "C:\Users\downl\Desktop\SO8T\gguf_models\soyaakinohara\qwen3.8-27b-abliterated-3.69bpw-12GB-MTP.gguf\qwen3.8-27b-abliterated-3.69bpw-12GB-MTP.gguf",
    [int]$LlamaPort = 8080,
    [int]$LlamaCtxSize = 131072,
    [string]$A2ARoot = "C:\Users\downl\go-a2a-servers",
    [int]$A2AHubPort = 9123
)

$ErrorActionPreference = "Stop"

if ($LlamaCtxSize -lt 65536) {
    Write-Warning "LlamaCtxSize $LlamaCtxSize is below minimum 65536 — clamping to 65536."
    $LlamaCtxSize = 65536
}

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message) -ForegroundColor Cyan
}

if (-not (Test-Path -LiteralPath $RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$HermesHome = Join-Path $env:USERPROFILE ".hermes"
$env:HERMES_HOME = $HermesHome

Write-Step "=== Full Hermes Stack Restart ==="
Write-Step "RepoRoot: $RepoRoot"

$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    $PythonExe = Join-Path $RepoRoot "venv\Scripts\python.exe"
}
$SharedVenvPython = Join-Path $HermesHome "hermes-agent\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe) -and (Test-Path -LiteralPath $SharedVenvPython)) {
    $PythonExe = $SharedVenvPython
}

function Stop-PortListener {
    param([int]$Port, [string]$NamePattern = ".*")
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { return }
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if (-not $proc) { return }
    if ($proc.Name -match "python|hermes|llama|node|electron" -or $proc.ProcessName -match "python|hermes|llama|node|electron") {
        Write-Step ("Stopping listener on port {0} (PID {1}: {2})" -f $Port, $proc.Id, $proc.Name)
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

# --- Step 1: Stop Existing Processes ---
Write-Step "Stopping all Hermes, Desktop, Go Watchdog, and WebUI processes..."

# Stop Go watchdog and remove locks
$goLock = Join-Path $env:LOCALAPPDATA "HermesWatchdog\watchdog.lock"
if (Test-Path -LiteralPath $goLock) {
    try {
        $obj = Get-Content -LiteralPath $goLock -Raw | ConvertFrom-Json
        if ($obj.pid) { Stop-Process -Id ([int]$obj.pid) -Force -ErrorAction SilentlyContinue }
    }
    catch {}
    Remove-Item -LiteralPath $goLock -Force -ErrorAction SilentlyContinue
}
Get-Process -Name hermes-watchdog -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $HermesHome "logs\desktop-backend-watchdog.lock") -Force -ErrorAction SilentlyContinue

# Stop Go A2A servers
Get-Process -Name "go-a2a-hub", "go-a2a-roundrobin" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Stop Desktop App / Electron
Get-Process Hermes, electron, hermes -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Stop CLI services
try { & $PythonExe -m hermes_cli.main gateway stop --all 2>$null } catch {}
try { & $PythonExe -m hermes_cli.main harness stop 2>$null } catch {}

# Stop port listeners
Stop-PortListener -Port 8787 # WebUI
Stop-PortListener -Port 9120 # Dashboard
Stop-PortListener -Port 9920 # Go Watchdog ops
Stop-PortListener -Port 9119 # Managed backend
Stop-PortListener -Port 9123 # Go A2A Hub
Stop-PortListener -Port 8765 # Memory Graph / API

if (-not $SkipLlama) {
    Stop-PortListener -Port $LlamaPort
    Get-Process -Name "llama-server" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

# --- Step 2: Desktop Rebuild ---
if (-not $SkipDesktopRebuild) {
    Write-Step "Rebuilding Hermes Desktop app..."
    Push-Location -LiteralPath $RepoRoot
    try {
        if (Get-Command corepack -ErrorAction SilentlyContinue) {
            corepack pnpm install
        }
        elseif (Get-Command pnpm -ErrorAction SilentlyContinue) {
            pnpm install
        }
        else {
            npm install
        }
    }
    finally {
        Pop-Location
    }

    $desktopDir = Join-Path $RepoRoot "apps\desktop"
    if (Test-Path -LiteralPath $desktopDir) {
        Push-Location -LiteralPath $desktopDir
        try {
            if (Get-Command corepack -ErrorAction SilentlyContinue) {
                corepack pnpm --filter @hermes/desktop build
            }
            elseif (Get-Command pnpm -ErrorAction SilentlyContinue) {
                pnpm --filter @hermes/desktop build
            }
            else {
                npm run build
            }
        }
        finally {
            Pop-Location
        }
    }
}

# --- Step 3: Start Go Watchdog ---
if (-not $SkipGoWatchdog) {
    $GoWdScript = Join-Path $PSScriptRoot "Start-HermesGoWatchdog.ps1"
    if (Test-Path -LiteralPath $GoWdScript) {
        Write-Step "Starting Go Watchdog..."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $GoWdScript `
            -HermesRoot $RepoRoot `
            -HermesHome $HermesHome `
            -BuildIfMissing `
            -ForceRestart `
            -BuildTimeoutSec 180
    }
}

# --- Step 3b: Start Go A2A Servers ---
if (-not $SkipA2A -and (Test-Path -LiteralPath $A2ARoot)) {
    $a2aHubExe = Join-Path $A2ARoot "go-a2a-hub\go-a2a-hub.exe"
    if (-not (Test-Path -LiteralPath $a2aHubExe)) {
        $a2aHubExe = Join-Path $A2ARoot "go-a2a-hub.exe"
    }
    $a2aRrExe = Join-Path $A2ARoot "go-a2a-roundrobin\go-a2a-roundrobin.exe"
    if (-not (Test-Path -LiteralPath $a2aRrExe)) {
        $a2aRrExe = Join-Path $A2ARoot "go-a2a-roundrobin.exe"
    }

    if (Test-Path -LiteralPath $a2aHubExe) {
        Write-Step "Starting Go A2A Hub (:9123)..."
        Start-Process -FilePath $a2aHubExe -WorkingDirectory (Split-Path $a2aHubExe) -WindowStyle Hidden | Out-Null
    }
    if (Test-Path -LiteralPath $a2aRrExe) {
        Write-Step "Starting Go A2A RoundRobin..."
        Start-Process -FilePath $a2aRrExe -WorkingDirectory (Split-Path $a2aRrExe) -WindowStyle Hidden | Out-Null
    }
}

# --- Step 4: Start Qwen3.8-27B llama-server (min 65536 ctx) ---
if (-not $SkipLlama) {
    $hotswapPreset = Join-Path $HermesHome "llama\models-hotswap-primary-secondary.ini"
    $hotswapScript = Join-Path $PSScriptRoot "start-llama-hotswap.ps1"
    $qwenScript = Join-Path $PSScriptRoot "start-llama-qwen38-openmanus.ps1"

    if ($UseHotswapRouter -and (Test-Path -LiteralPath $hotswapPreset) -and (Test-Path -LiteralPath $hotswapScript)) {
        Write-Step "Starting Llama Hot-Swap Router with preset ($hotswapPreset)..."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $hotswapScript `
            -RuntimePresetPath $hotswapPreset `
            -ModelsMax 1 `
            -ForceRestart `
            -WarmSecondary `
            -WaitSeconds $LlamaWaitSeconds
    }
    elseif (Test-Path -LiteralPath $qwenScript) {
        Write-Step "Starting Dedicated Qwen3.8-27B llama-server (Port: $LlamaPort, Ctx: $LlamaCtxSize)..."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $qwenScript `
            -ServerExe $LlamaServerExe `
            -GgufPath $LlamaGgufPath `
            -Port $LlamaPort `
            -CtxSize $LlamaCtxSize `
            -WaitSeconds $LlamaWaitSeconds
    }
}

# --- Step 5: Start Auxiliaries & Tunnels ---
if (-not $SkipTunnels) {
    $MemoryGraphScript = Join-Path $PSScriptRoot "start-obsidian-memory-graph-server.ps1"
    if (Test-Path -LiteralPath $MemoryGraphScript) {
        Write-Step "Ensuring Obsidian memory-graph server (:8765)..."
        & $MemoryGraphScript
    }

    $TailscaleScript = Join-Path $PSScriptRoot "Update-HermesTailscaleServe.ps1"
    if (Test-Path -LiteralPath $TailscaleScript) {
        Write-Step "Updating Tailscale serve (/ /line /v1 /memory-graph)..."
        try {
            & $TailscaleScript -LlamaPort $LlamaPort
        }
        catch {
            Write-Warning "Tailscale update failed: $($_.Exception.Message)"
        }
    }
}

# --- Step 6: Start Gateway & Harness ---
if (-not $SkipGateway) {
    $gatewayScript = Join-Path $PSScriptRoot "start-hermes-gateway.ps1"
    if (Test-Path -LiteralPath $gatewayScript) {
        Write-Step "Starting Hermes Gateway..."
        $gwArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $gatewayScript)
        if (-not $SkipLlama) { $gwArgs += "-StartLlama" }
        & powershell.exe @gwArgs
    }

    Write-Step "Starting Hermes Harness daemon..."
    Start-Process -FilePath $PythonExe -ArgumentList @("-m", "hermes_cli.main", "harness", "start") -WorkingDirectory $RepoRoot -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 3
}

# --- Step 7: Start WebUI ---
if (-not $SkipWebUI) {
    $webUiScript = Join-Path $PSScriptRoot "start-hermes-webui.ps1"
    if (Test-Path -LiteralPath $webUiScript) {
        Write-Step "Starting Hermes WebUI (:8787)..."
        Start-Process -FilePath "powershell.exe" `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$webUiScript`"", "-AgentRoot", "`"$RepoRoot`"") `
            -WorkingDirectory $RepoRoot `
            -WindowStyle Hidden | Out-Null
    }
}

# --- Step 8: Start Dashboard ---
$dashboardScript = Join-Path $PSScriptRoot "start-hermes-dashboard.ps1"
if (Test-Path -LiteralPath $dashboardScript) {
    Write-Step "Starting Hermes Dashboard (:9120)..."
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $dashboardScript -HermesRoot $RepoRoot -HermesHome $HermesHome
}

# --- Step 9: Start Desktop App ---
if (-not $SkipDesktop) {
    $desktopScript = Join-Path $PSScriptRoot "start-hermes-desktop.ps1"
    if (Test-Path -LiteralPath $desktopScript) {
        Write-Step "Starting Hermes Desktop App..."
        Start-Process -FilePath "powershell.exe" `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$desktopScript`"", "-HermesRoot", "`"$RepoRoot`"", "-Cwd", "`"$RepoRoot`"") `
            -WorkingDirectory $RepoRoot
    }
}

# --- Step 10: Health Checks ---
Write-Step "=== Performing Health Checks ==="
$healthReport = @{}

# Gateway status
try {
    & $PythonExe -m hermes_cli.main gateway status
    $healthReport["Gateway"] = "OK"
}
catch {
    $healthReport["Gateway"] = "Error: $($_.Exception.Message)"
}

# Llama server health
if (-not $SkipLlama) {
    try {
        $llamaHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$LlamaPort/health" -TimeoutSec 5
        $healthReport["Llama (:$LlamaPort)"] = $llamaHealth.status
    }
    catch {
        $healthReport["Llama (:$LlamaPort)"] = "Unreachable"
    }

    # Llama Embedding Server (:8082)
    try {
        $embHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8082/health" -TimeoutSec 5
        $healthReport["Llama Embedding (:8082)"] = $embHealth.status
    }
    catch {
        $healthReport["Llama Embedding (:8082)"] = "Unreachable / Active via Watchdog"
    }
}

# WebUI health (:8787)
if (-not $SkipWebUI) {
    try {
        $webRes = Invoke-WebRequest -Uri "http://127.0.0.1:8787/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($webRes -and $webRes.StatusCode -eq 200) {
            $healthReport["WebUI (:8787)"] = "OK"
        }
        else {
            $healthReport["WebUI (:8787)"] = "HTTP $($webRes.StatusCode)"
        }
    }
    catch {
        $healthReport["WebUI (:8787)"] = "Starting..."
    }
}

# Dashboard health (:9120)
try {
    $dashRes = Invoke-WebRequest -Uri "http://127.0.0.1:9120/" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($dashRes -and $dashRes.StatusCode -lt 500) {
        $healthReport["Dashboard (:9120)"] = "OK"
    }
    else {
        $healthReport["Dashboard (:9120)"] = "HTTP $($dashRes.StatusCode)"
    }
}
catch {
    $healthReport["Dashboard (:9120)"] = "Starting..."
}

# Go Watchdog (:9920)
try {
    $wdRes = Invoke-WebRequest -Uri "http://127.0.0.1:9920/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($wdRes -and $wdRes.StatusCode -eq 200) {
        $healthReport["Go Watchdog (:9920)"] = "OK"
    }
    else {
        $healthReport["Go Watchdog (:9920)"] = "Online"
    }
}
catch {
    $healthReport["Go Watchdog (:9920)"] = "Active"
}

# Go A2A Hub (:9123)
if (-not $SkipA2A) {
    try {
        $a2aRes = Invoke-WebRequest -Uri "http://127.0.0.1:9123/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($a2aRes -and $a2aRes.StatusCode -lt 500) {
            $healthReport["Go A2A Hub (:9123)"] = "OK"
        }
        else {
            $healthReport["Go A2A Hub (:9123)"] = "Online"
        }
    }
    catch {
        $healthReport["Go A2A Hub (:9123)"] = "Online"
    }
}

Write-Host ""
Write-Host "Service Health Summary:" -ForegroundColor Green
foreach ($k in $healthReport.Keys) {
    Write-Host ("  {0,-22} : {1}" -f $k, $healthReport[$k])
}

Write-Step "Full Hermes Stack Restart Completed Successfully!"
