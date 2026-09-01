#requires -version 5.0
<#
.SYNOPSIS
    Hermes スタック完全自動起動・再起動スクリプト (電源投入時 / 手動実行)
    WebUI・フルスタック対応版

.DESCRIPTION
    Windows ログオン後に以下のサービスを順番に立ち上げる PowerShell スクリプト。

    対応サービス:
    - Hermes Desktop (Electron) : ビルドチェック → 未ビルドならビルド → 起動
    - ローカル llama-server (埋め込み系) : GGUF モデルの KVキャッシュ込み Inference
    - Hermes WebUI (ダッシュボード) : ポート 3000 番台のウェブUI
    - Hermes Gateway (メッセージングゲートウェイ) : 必要に応じて起動
    - Go A2A ハブサーバー (go-a2a-hub) : ポート 9123 で A2A メッセージ受付
    - Go A2A ラウンドロビンサーバー (go-a2a-roundrobin) : seed42 確定的回転

    電源投入時の自動実行はスタートアップフォルダ shortcut かタスクスケジューラで行う。
    再起動したい場合は -Restart スイッチを付けると各サービスを graceful に再起動する。

    手動実行時: powershell -ExecutionPolicy Bypass -File .\\hermes-stack-restart.ps1 [-Restart] [-Desktop] [-Llama] [-WebUI] [-Gateway] [-A2A] [-All] [-FullStack]

.EXAMPLE
    .\\hermes-stack-restart.ps1 -All             # Desktop + Llama + WebUI + A2A 起動
    .\\hermes-stack-restart.ps1 -FullStack       # ゲートウェイ含むフルスタック起動
    .\\hermes-stack-restart.ps1 -Restart         # 既存プロセスがあれば再起動
    .\\hermes-stack-restart.ps1 -Desktop         # デスクトップだけ
    .\\hermes-stack-restart.ps1 -A2A             # Go A2A サーバーだけ
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# === 共通設定（環境に合わせて調整） =============================================

$HERMES_ROOT = 'C:\Users\downl\Documents\New project\hermes-agent'
$DESKTOP_EXE = Join-Path $HERMES_ROOT 'apps\desktop\release\win-unpacked\Hermes.exe'
$DESKTOP_DIR = Join-Path $HERMES_ROOT 'apps\desktop'
$WEBUI_DIR   = Join-Path $HERMES_ROOT 'web'
$WEBUI_PORT  = 3000
$LLAMA_SERVER = 'C:\Users\downl\Desktop\Turboquant-CUDA\zapabob\llama.cpp\build-codex-rtx5060ti-msvc\bin\llama-server.exe'
$LLAMA_MODEL = 'E:\ComfyUI_models\qwen\Qwen3.8-27B-Abliterated-mtp-Q4_K_M.gguf'
$LLAMA_CTX   = 65536
$LLAMA_PORT  = 8080
$A2A_ROOT     = 'C:\Users\downl\go-a2a-servers'
$A2A_HUB_EXE  = Join-Path $A2A_ROOT 'go-a2a-hub\go-a2a-hub.exe'
$A2A_RR_EXE   = Join-Path $A2A_ROOT 'go-a2a-roundrobin\go-a2a-roundrobin.exe'
$A2A_HUB_PORT = 9123
$A2A_WORK_DIR = $A2A_ROOT
$STARTUP_DIR  = [Environment]::GetFolderPath('Startup')
$LOG_DIR      = 'C:\Users\downl\.hermes\logs'
$LAUNCH_LOG   = Join-Path $LOG_DIR 'hermes-stack-launch.log'

$procNames = @{
    Desktop    = 'Hermes'
    Llama      = 'llama-server'
    WebUI      = 'node'
    Gateway    = 'hermes'
    Hub        = 'go-a2a-hub'
    RoundRobin = 'go-a2a-roundrobin'
}

# =========================================================

function Write-LaunchLog {
    param([string]$Message)
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$ts] $Message"
    Add-Content -Path $LAUNCH_LOG -Value $line -Encoding UTF8
    Write-Host $line
}

function Stop-ProcByName {
    param([string]$Name)
    Get-Process -Name $Name -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}

function Test-PortFree {
    param([int]$Port)
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
        $free = $true
    } catch {
        $free = $false
    } finally {
        $listener.Stop()
    }
    return $free
}

function Test-ExeExists {
    param([string]$Path)
    return (Test-Path $Path) -and (Get-Item $Path).Extension -eq '.exe'
}

# === デスクトップ起動 =================================================

function Start-Desktop {
    if (-not (Test-ExeExists $DESKTOP_EXE)) {
        Write-LaunchLog "[Desktop] ERROR: Hermes.exe missing at $DESKTOP_EXE"
        Write-LaunchLog "[Desktop] ビルドが必要です: cd apps/desktop && npm run build"
        return $false
    }
    Write-LaunchLog "[Desktop] Starting Hermes.exe"
    $proc = Start-Process -FilePath $DESKTOP_EXE -PassThru -WorkingDirectory $DESKTOP_DIR
    Start-Sleep -Seconds 5
    if ($proc.HasExited) {
        Write-LaunchLog "[Desktop] Hermes.exe exited immediately (exit code $($proc.ExitCode))"
        return $false
    }
    Write-LaunchLog "[Desktop] Hermes.exe started (PID $($proc.Id))."
    return $true
}

# === WebUI 起動 =====================================================

function Start-WebUI {
    Write-LaunchLog "[WebUI] Starting Hermes WebUI..."
    if (-not (Test-Path (Join-Path $WEBUI_DIR 'package.json'))) {
        Write-LaunchLog "[WebUI] WARNING: package.json not found in $WEBUI_DIR — skipping."
        return $false
    }
    if (-not (Test-PortFree $WEBUI_PORT)) {
        Write-LaunchLog "[WebUI] Port $WEBUI_PORT in use — skip."
        return $true
    }
    $proc = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','start','--','-p',$WEBUI_PORT `
        -WorkingDirectory $WEBUI_DIR -PassThru -NoNewWindow
    Start-Sleep -Seconds 5
    if ($proc.HasExited) {
        Write-LaunchLog "[WebUI] node exited immediately (exit code $($proc.ExitCode))."
        return $false
    }
    Write-LaunchLog "[WebUI] WebUI started (PID $($proc.Id))."
    return $true
}

# === Gateway 起動 ====================================================

function Start-Gateway {
    Write-LaunchLog "[Gateway] Starting Hermes Gateway..."
    $venvPy = Join-Path $HERMES_ROOT '.venv\Scripts\python.exe'
    if (-not (Test-Path $venvPy)) {
        Write-LaunchLog "[Gateway] ERROR: .venv\Scripts\python.exe not found"
        return $false
    }
    $env:PYTHONPATH = $HERMES_ROOT
    $proc = Start-Process -FilePath $venvPy -ArgumentList '-m','hermes_cli.main','serve' `
        -WorkingDirectory $HERMES_ROOT -PassThru -NoNewWindow
    Start-Sleep -Seconds 5
    if ($proc.HasExited) {
        Write-LaunchLog "[Gateway] hermes serve exited immediately (exit code $($proc.ExitCode))."
        return $false
    }
    Write-LaunchLog "[Gateway] Gateway started (PID $($proc.Id))."
    return $true
}

# === llama-server 起動 =================================================

function Start-Llama {
    if (-not (Test-ExeExists $LLAMA_SERVER)) {
        Write-LaunchLog "[Llama] ERROR: llama-server.exe missing at $LLAMA_SERVER"
        return $false
    }
    if (-not (Test-Path $LLAMA_MODEL)) {
        Write-LaunchLog "[Llama] WARNING: model not found at $LLAMA_MODEL — skipping start."
        return $false
    }
    if (-not (Test-PortFree $LLAMA_PORT)) {
        Write-LaunchLog "[Llama] Port $LLAMA_PORT in use — assuming server is running."
        return $true
    }
    Write-LaunchLog "[Llama] Starting llama-server on port $LLAMA_PORT (ctx $LLAMA_CTX)"
    $args = @(
        '--model', $LLAMA_MODEL,
        '--port', $LLAMA_PORT,
        '--ctx-size', $LLAMA_CTX,
        '--parallel', '1'
    )
    $env:LLAMA_ARG_FLAGS = ''
    $proc = Start-Process -FilePath $LLAMA_SERVER -ArgumentList $args -PassThru -NoNewWindow
    Start-Sleep -Seconds 8
    if ($proc.HasExited) {
        Write-LaunchLog "[Llama] llama-server exited immediately (exit code $($proc.ExitCode))."
        return $false
    }
    Write-LaunchLog "[Llama] llama-server started (PID $($proc.Id))."
    return $true
}

# === Go A2A サーバー起動 =============================================

function Start-GoA2A {
    Write-LaunchLog '[A2A] Starting Go A2A servers...'
    if (Test-ExeExists $A2A_HUB_EXE) {
        if (-not (Test-PortFree $A2A_HUB_PORT)) {
            Write-LaunchLog "[A2A] Hub port $A2A_HUB_PORT in use — skip."
        } else {
            Write-LaunchLog "[A2A] Starting go-a2a-hub.exe on port $A2A_HUB_PORT"
            $proc = Start-Process -FilePath $A2A_HUB_EXE -WorkingDirectory $A2A_WORK_DIR -PassThru -WindowStyle Hidden
            Start-Sleep -Seconds 3
            if ($proc.HasExited) {
                Write-LaunchLog "[A2A] go-a2a-hub exited immediately (exit code $($proc.ExitCode))."
            } else {
                Write-LaunchLog "[A2A] go-a2a-hub started (PID $($proc.Id))."
            }
        }
    } else {
        Write-LaunchLog "[A2A] WARNING: go-a2a-hub.exe missing at $A2A_HUB_EXE"
    }
    if (Test-ExeExists $A2A_RR_EXE) {
        Write-LaunchLog "[A2A] Starting go-a2a-roundrobin.exe"
        $proc = Start-Process -FilePath $A2A_RR_EXE -WorkingDirectory $A2A_WORK_DIR -PassThru -WindowStyle Hidden
        Start-Sleep -Seconds 3
        if ($proc.HasExited) {
            Write-LaunchLog "[A2A] go-a2a-roundrobin exited immediately (exit code $($proc.ExitCode))."
        } else {
            Write-LaunchLog "[A2A] go-a2a-roundrobin started (PID $($proc.Id))."
        }
    } else {
        Write-LaunchLog "[A2A] WARNING: go-a2a-roundrobin.exe missing at $A2A_RR_EXE"
    }
    return $true
}

# === 共通再起動フロー ================================================

function Restart-One {
    param(
        [string]$Key,
        [scriptblock]$StartBlock
    )
    Write-LaunchLog "[$Key] 正在再起動中..."
    Stop-ProcByName $procNames[$Key]
    & $StartBlock
    Start-Sleep -Seconds 2
}

function Restart-All {
    Write-LaunchLog '=== 全サービス再起動開始 ==='
    Restart-One -Key 'Desktop'    -StartBlock { Start-Desktop }
    Restart-One -Key 'Llama'      -StartBlock { Start-Llama }
    Restart-One -Key 'WebUI'      -StartBlock { Start-WebUI }
    Restart-One -Key 'Gateway'    -StartBlock { Start-Gateway }
    Restart-One -Key 'A2A'        -StartBlock { Start-GoA2A }
    Write-LaunchLog '=== 全サービス再起動完了 ==='
}

function Restart-FullStack {
    Write-LaunchLog '=== フルスタック再起動開始 ==='
    Restart-One -Key 'Desktop'    -StartBlock { Start-Desktop }
    Restart-One -Key 'Llama'      -StartBlock { Start-Llama }
    Restart-One -Key 'WebUI'      -StartBlock { Start-WebUI }
    Restart-One -Key 'Gateway'    -StartBlock { Start-Gateway }
    Restart-One -Key 'A2A'        -StartBlock { Start-GoA2A }
    Write-LaunchLog '=== フルスタック再起動完了 ==='
}

# === メイン ===========================================================

$doDesktop   = $false
$doLlama     = $false
$doWebUI     = $false
$doGateway   = $false
$doA2A       = $false
$doRestart   = $false
$doFullStack = $false

for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        '-Desktop'    { $doDesktop  = $true }
        '-Llama'      { $doLlama    = $true }
        '-WebUI'      { $doWebUI    = $true }
        '-Gateway'    { $doGateway  = $true }
        '-A2A'        { $doA2A      = $true }
        '-Restart'    { $doRestart  = $true }
        '-All'        { $doDesktop = $true; $doLlama = $true; $doWebUI = $true; $doA2A = $true }
        '-FullStack'  { $doDesktop = $true; $doLlama = $true; $doWebUI = $true; $doGateway = $true; $doA2A = $true }
    }
}

if (-not ($doDesktop -or $doLlama -or $doWebUI -or $doGateway -or $doA2A -or $doRestart -or $doFullStack)) {
    $doDesktop = $true
    $doLlama   = $true
    $doWebUI   = $true
    $doA2A     = $true
}

if (-not (Test-Path $LOG_DIR)) {
    New-Item -Path $LOG_DIR -ItemType Directory -Force | Out-Null
}

Write-LaunchLog '=== Hermes スタック起動スクリプト開始 ==='
Write-LaunchLog "Desktop: $doDesktop | Llama: $doLlama | WebUI: $doWebUI | Gateway: $doGateway | A2A: $doA2A | Restart: $doRestart | FullStack: $doFullStack"

if ($doFullStack) {
    Restart-FullStack
} elseif ($doRestart) {
    Restart-All
} else {
    if ($doDesktop)  { Start-Desktop  }
    if ($doLlama)    { Start-Llama    }
    if ($doWebUI)    { Start-WebUI    }
    if ($doGateway)  { Start-Gateway  }
    if ($doA2A)      { Start-GoA2A    }
}

Write-LaunchLog '=== 完了 ==='
