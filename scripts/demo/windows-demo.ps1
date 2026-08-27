param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path,
    [string]$InstallerPath = "",
    [string]$DemoRoot = (Join-Path $env:TEMP "Hermes Windows Workstation Demo $([guid]::NewGuid())"),
    [string]$ModelId = "local-model",
    [string]$LlamaBaseUrl = "http://127.0.0.1:8080/v1",
    [string]$ConversationPrompt = "Reply with the product name and one short sentence.",
    [int]$WatchdogPort = 19920,
    [int]$BackendPort = 19119,
    [switch]$RunConversation,
    [switch]$ExerciseRecovery,
    [switch]$AllowPartial,
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $RepoRoot).Path
$demo = [System.IO.Path]::GetFullPath($DemoRoot)
if (Test-Path -LiteralPath $demo) {
    throw "DemoRoot already exists; choose a new dedicated directory: $demo"
}
$profileHome = Join-Path $demo "profile"
$installRoot = Join-Path $demo "installed"
$watchdogData = Join-Path $demo "watchdog"
$reportPath = if ($OutputPath) {
    [System.IO.Path]::GetFullPath($OutputPath)
} else {
    Join-Path $demo "windows-demo.json"
}
New-Item -ItemType Directory -Path $profileHome, $watchdogData -Force | Out-Null

$llamaUri = [Uri]$LlamaBaseUrl
if (-not $llamaUri.IsLoopback) {
    throw "The demo accepts only a loopback local-model endpoint"
}
if ($ModelId -match "[\r\n]") {
    throw "ModelId must be one line"
}

function Test-HttpEndpoint {
    param([string]$Uri, [int]$TimeoutSec = 5)
    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec $TimeoutSec
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    } catch {
        return $false
    }
}

function Wait-HttpEndpoint {
    param([string]$Uri, [int]$TimeoutSec)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    do {
        if (Test-HttpEndpoint $Uri) {
            return $true
        }
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $deadline)
    return $false
}

function Get-SessionIdFromText {
    param([string]$Text)
    $match = [regex]::Match(
        $Text,
        "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )
    return if ($match.Success) { $match.Value } else { "" }
}

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $sharedVenvPython = [System.IO.Path]::GetFullPath(
        (Join-Path $root "..\..\.venv\Scripts\python.exe")
    )
    if (Test-Path -LiteralPath $sharedVenvPython) {
        $python = $sharedVenvPython
    } else {
        $python = (Get-Command python -ErrorAction Stop).Source
    }
}
$distribution = Get-Content -LiteralPath (Join-Path $root "downstream\distribution.json") -Raw |
    ConvertFrom-Json
$downstreamSha = (& git -C $root rev-parse HEAD).Trim()
$results = [ordered]@{
    clean_install = "not_run"
    cli_version = "failed"
    desktop_launch = "not_run"
    local_agent_conversation = "not_run"
    local_llama_provider = "failed"
    watchdog_status = "not_run"
    supervised_backend_recovery = "not_run"
    session_persistence = "not_run"
    downstream_identity = "failed"
}
$desktop = $null
$demoDesktopProcess = $null
$watchdogProcess = $null
$previousHermesHome = [Environment]::GetEnvironmentVariable("HERMES_HOME", "Process")
$previousFallbackAutostart = [Environment]::GetEnvironmentVariable(
    "HERMES_LLAMA_FALLBACK_AUTOSTART",
    "Process"
)

try {
    [Environment]::SetEnvironmentVariable("HERMES_HOME", $profileHome, "Process")
    [Environment]::SetEnvironmentVariable(
        "HERMES_LLAMA_FALLBACK_AUTOSTART",
        "false",
        "Process"
    )
    $modelYaml = ConvertTo-Json $ModelId -Compress
    $baseUrlYaml = ConvertTo-Json $LlamaBaseUrl -Compress
    $config = @(
        "model:",
        "  provider: custom",
        "  default: $modelYaml",
        "  base_url: $baseUrlYaml",
        "  api_key: local",
        "  api_mode: chat_completions"
    ) -join [Environment]::NewLine
    [System.IO.File]::WriteAllText(
        (Join-Path $profileHome "config.yaml"),
        ($config + [Environment]::NewLine),
        [System.Text.UTF8Encoding]::new($false)
    )

    if ($InstallerPath) {
        $installer = (Resolve-Path -LiteralPath $InstallerPath).Path
        New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
        $installerProcess = Start-Process -FilePath $installer `
            -ArgumentList @("/S", "/D=$installRoot") `
            -Wait `
            -PassThru `
            -WindowStyle Hidden
        if ($installerProcess.ExitCode -ne 0) {
            throw "Installer exited with code $($installerProcess.ExitCode)"
        }
        $desktop = Get-ChildItem -LiteralPath $installRoot -Filter "Hermes.exe" -File -Recurse |
            Select-Object -First 1
        if (-not $desktop) {
            throw "The dedicated demo installation does not contain Hermes.exe"
        }
        $resourceRoot = Join-Path $desktop.Directory.FullName "resources"
        $packagedDistributionPath = Join-Path $resourceRoot "distribution\distribution.json"
        $installStampPath = Join-Path $resourceRoot "install-stamp.json"
        if (
            -not (Test-Path -LiteralPath $packagedDistributionPath) -or
            -not (Test-Path -LiteralPath $installStampPath)
        ) {
            throw "The demo installation is missing distribution or exact-SHA metadata"
        }
        $packagedDistribution = Get-Content -LiteralPath $packagedDistributionPath -Raw |
            ConvertFrom-Json
        $installStamp = Get-Content -LiteralPath $installStampPath -Raw | ConvertFrom-Json
        $desktopVersion = (Get-Item -LiteralPath $desktop.FullName).VersionInfo
        if (
            $packagedDistribution.id -ne $distribution.id -or
            $packagedDistribution.version -ne $distribution.version -or
            $desktopVersion.InternalName -ne $distribution.id -or
            $desktopVersion.SpecialBuild -ne $distribution.version -or
            $installStamp.commit -ne $downstreamSha -or
            $installStamp.dirty -ne $false
        ) {
            throw "The installed Desktop identity does not match the exact clean candidate"
        }
        $results.clean_install = "passed"
        $results.downstream_identity = "passed"
    }

    $versionText = (& $python -m hermes_cli.main --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and $versionText -match [regex]::Escape($distribution.version)) {
        $results.cli_version = "passed"
    }

    if ($desktop) {
        $demoDesktopProcess = Start-Process -FilePath $desktop.FullName `
            -PassThru `
            -WindowStyle Hidden
        Start-Sleep -Seconds 8
        $results.desktop_launch = if ($demoDesktopProcess.HasExited) { "failed" } else { "passed" }
    }

    $modelsUrl = $LlamaBaseUrl.TrimEnd("/") + "/models"
    $results.local_llama_provider = if (Test-HttpEndpoint $modelsUrl) {
        "passed"
    } else {
        "failed"
    }

    $sessionBeforeRecovery = ""
    if ($RunConversation -and $results.local_llama_provider -eq "passed") {
        & $python -m hermes_cli.main `
            --ignore-rules `
            --provider custom `
            --model $ModelId `
            chat `
            --query $ConversationPrompt
        if ($LASTEXITCODE -eq 0) {
            $results.local_agent_conversation = "passed"
            $sessionList = (& $python -m hermes_cli.main sessions list --limit 20 2>&1 | Out-String)
            $sessionBeforeRecovery = Get-SessionIdFromText $sessionList
        } else {
            $results.local_agent_conversation = "failed"
        }
    }

    if ($ExerciseRecovery) {
        if (-not $desktop) {
            throw "ExerciseRecovery requires InstallerPath"
        }
        $foreignDesktop = @(Get-CimInstance Win32_Process -Filter "Name = 'Hermes.exe'" |
            Where-Object {
                $_.ExecutablePath -and
                -not $_.ExecutablePath.StartsWith(
                    $installRoot,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            })
        if ($foreignDesktop.Count -gt 0) {
            throw "Recovery demo requires a clean workstation without another Hermes.exe"
        }
        $watchdogExe = Join-Path $root "scripts\windows\watchdog-go\dist\hermes-watchdog.exe"
        if (-not (Test-Path -LiteralPath $watchdogExe)) {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
                (Join-Path $root "scripts\windows\Build-HermesGoWatchdog.ps1")
            if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $watchdogExe)) {
                throw "Could not build the dedicated demo watchdog"
            }
        }
        $watchdogUrl = "http://127.0.0.1:$WatchdogPort/api/status"
        $backendUrl = "http://127.0.0.1:$BackendPort/api/status"
        if ((Test-HttpEndpoint $watchdogUrl) -or (Test-HttpEndpoint $backendUrl)) {
            throw "Dedicated demo ports are already in use"
        }
        $watchdogArguments = @(
            "-hermes-root", ('"' + $root + '"'),
            "-hermes-home", ('"' + $profileHome + '"'),
            "-packaged-exe", ('"' + $desktop.FullName + '"'),
            "-data-dir", ('"' + $watchdogData + '"'),
            "-listen", "127.0.0.1:$WatchdogPort",
            "-managed-backend-port", "$BackendPort",
            "-interval", "2",
            "-fail-threshold", "2"
        )
        $watchdogProcess = Start-Process -FilePath $watchdogExe `
            -ArgumentList $watchdogArguments `
            -PassThru `
            -WindowStyle Hidden
        if (-not (Wait-HttpEndpoint $watchdogUrl 30)) {
            throw "Dedicated watchdog did not become ready"
        }
        if ($watchdogProcess.HasExited) {
            throw "Dedicated watchdog exited before qualification"
        }
        if (-not (Wait-HttpEndpoint $backendUrl 180)) {
            throw "Dedicated managed backend did not become ready"
        }
        $results.watchdog_status = "passed"
        $before = Invoke-RestMethod -Uri $watchdogUrl -TimeoutSec 5
        $backendPid = [int]$before.backendPid
        if ($backendPid -le 0) {
            throw "Dedicated watchdog did not report a managed backend PID"
        }
        Stop-Process -Id $backendPid -Force
        $recovered = $false
        $deadline = [DateTime]::UtcNow.AddSeconds(180)
        do {
            Start-Sleep -Seconds 2
            try {
                $after = Invoke-RestMethod -Uri $watchdogUrl -TimeoutSec 5
                $newPid = [int]$after.backendPid
                if ($newPid -gt 0 -and $newPid -ne $backendPid -and (Test-HttpEndpoint $backendUrl)) {
                    $recovered = $true
                    break
                }
            } catch {}
        } while ([DateTime]::UtcNow -lt $deadline)
        $results.supervised_backend_recovery = if ($recovered) { "passed" } else { "failed" }
        if ($sessionBeforeRecovery) {
            $sessionListAfter = (& $python -m hermes_cli.main sessions list --limit 20 2>&1 | Out-String)
            $results.session_persistence = if (
                $sessionListAfter -match [regex]::Escape($sessionBeforeRecovery)
            ) { "passed" } else { "failed" }
        }
    }
} finally {
    if ($watchdogProcess -and -not $watchdogProcess.HasExited) {
        Stop-Process -Id $watchdogProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($demoDesktopProcess -and -not $demoDesktopProcess.HasExited) {
        Stop-Process -Id $demoDesktopProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $installRoot) {
        $ownedRoot = [System.IO.Path]::GetFullPath($installRoot).TrimEnd('\') + '\'
        $ownedProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.ExecutablePath -and
                $_.ExecutablePath.StartsWith(
                    $ownedRoot,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            })
        if ($ownedProcesses.Count -gt 0) {
            Stop-Process -Id @($ownedProcesses.ProcessId) -Force -ErrorAction SilentlyContinue
        }
    }
    [Environment]::SetEnvironmentVariable("HERMES_HOME", $previousHermesHome, "Process")
    [Environment]::SetEnvironmentVariable(
        "HERMES_LLAMA_FALLBACK_AUTOSTART",
        $previousFallbackAutostart,
        "Process"
    )
}

$required = @(
    "clean_install", "cli_version", "desktop_launch", "local_llama_provider",
    "downstream_identity"
)
if ($RunConversation) {
    $required += "local_agent_conversation"
}
if ($ExerciseRecovery) {
    $required += @("watchdog_status", "supervised_backend_recovery", "session_persistence")
}
$status = if (@($required | Where-Object { $results[$_] -ne "passed" }).Count -eq 0) {
    "passed"
} else {
    "failed"
}
$report = [ordered]@{
    schema_version = 1
    status = $status
    downstream_commit_sha = $downstreamSha
    upstream_snapshot_sha = [string]$distribution.upstream.snapshot_sha
    distribution_version = [string]$distribution.version
    dedicated_demo_profile = $true
    results = $results
}
$reportDirectory = Split-Path -Parent $reportPath
if ($reportDirectory) {
    New-Item -ItemType Directory -Path $reportDirectory -Force | Out-Null
}
[System.IO.File]::WriteAllText(
    $reportPath,
    (($report | ConvertTo-Json -Depth 8) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false)
)
$report | ConvertTo-Json -Depth 8
if ($status -ne "passed" -and -not $AllowPartial) {
    throw "Windows demo failed or remains incomplete"
}
