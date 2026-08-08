# Start Go-based Hermes Desktop<->backend watchdog (operator-only; NOT agent-reachable).
[CmdletBinding()]
param(
    [int]$IntervalSec = 20,
    [int]$FailThreshold = 2,
    [switch]$Once,
    [switch]$NoPrewarm,
    [switch]$ManageDesktop,
    [switch]$NoTsnet,
    [string]$Listen = "127.0.0.1:9920",
    [string]$HermesRoot = "",
    [string]$HermesHome = "",
    [switch]$BuildIfMissing,
    [switch]$ForceRestart,
    # Build a side-by-side candidate, stop only the watchdog, atomically replace
    # the executable, then prove the replacement through /health.
    [switch]$HotSwap,
    [int]$HotSwapTimeoutSec = 30,
    # Optional installed watchdog target. This lets a checked-out branch build
    # the candidate while replacing the live runtime atomically.
    [string]$RuntimeExe = "",
    # Bound go build so restart-hermes-stack never hangs on go mod tidy / network.
    [int]$BuildTimeoutSec = 180,
    # Default skip go test for the operator start path (full test via Build-HermesGoWatchdog.ps1).
    [switch]$RunBuildTests,
    # Watchdog-managed hermes serve stays distinct from Desktop :9119, dashboard
    # :9120, WebUI :8787, and the watchdog control plane :9920.
    [int]$ManagedBackendPort = 9118
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = if ($HermesRoot) { $HermesRoot } else { (Resolve-Path (Join-Path $ScriptDir "..\..")).Path }
if (-not $HermesHome) { $HermesHome = Join-Path $env:USERPROFILE ".hermes" }

$SourceExe = Join-Path $ScriptDir "watchdog-go\dist\hermes-watchdog.exe"
if ($RuntimeExe) {
    if (-not $HotSwap) {
        throw "-RuntimeExe is only supported with -HotSwap"
    }
    $Exe = [System.IO.Path]::GetFullPath($RuntimeExe)
} else {
    $Exe = $SourceExe
}
$CandidateExe = Join-Path (Split-Path -Parent $SourceExe) "hermes-watchdog.next.exe"
$DataDir = Join-Path $env:LOCALAPPDATA "HermesWatchdog"
$LockPath = Join-Path $DataDir "watchdog.lock"

function Invoke-GoWatchdogBuildBounded {
    param(
        [string]$BuildScript,
        [int]$TimeoutSec,
        [string]$OutputName,
        [switch]$SkipTest
    )
    $argList = @("-OutputName", $OutputName)
    if ($SkipTest) { $argList += "-SkipTest" }
    Write-Host ("Building Go watchdog (timeout={0}s, SkipTest={1}, output={2})..." -f $TimeoutSec, [bool]$SkipTest, $OutputName)
    $proc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $BuildScript) + $argList) `
        -WorkingDirectory $ScriptDir `
        -PassThru `
        -WindowStyle Hidden
    if (-not $proc) {
        throw "Failed to start Build-HermesGoWatchdog.ps1"
    }
    $finished = $proc.WaitForExit($TimeoutSec * 1000)
    if (-not $finished) {
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        # Also kill orphaned go children from the timed-out build.
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -and $_.CommandLine -match 'watchdog-go' -and $_.Name -match '^(go|compile|link)\.exe$'
        } | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
        throw "Go watchdog build timed out after ${TimeoutSec}s"
    }
    if ($proc.ExitCode -ne 0) {
        throw "Go watchdog build failed (exit $($proc.ExitCode))"
    }
}

function Get-GoWatchdogPid {
    if (-not (Test-Path -LiteralPath $LockPath)) { return $null }
    try {
        $obj = Get-Content -LiteralPath $LockPath -Raw | ConvertFrom-Json
        $watchdogPid = [int]$obj.pid
        if ($watchdogPid -le 0) { return $null }
        if (Get-Process -Id $watchdogPid -ErrorAction SilentlyContinue) {
            return $watchdogPid
        }
    } catch {}
    return $null
}

function Test-GoWatchdogAlive {
    return $null -ne (Get-GoWatchdogPid)
}

function Wait-GoWatchdogExit {
    param(
        [int]$ProcessId,
        [int]$TimeoutSec
    )
    if ($ProcessId -le 0) { return $true }
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return -not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Get-LocalWatchdogBaseUri {
    param([string]$ListenAddress)
    if ($ListenAddress -match '^(127\.0\.0\.1|localhost):([0-9]{1,5})$') {
        return ("http://{0}:{1}" -f $Matches[1], $Matches[2])
    }
    return $null
}

function Request-GoWatchdogStop {
    $baseUri = Get-LocalWatchdogBaseUri -ListenAddress $Listen
    $adminToken = [string]$env:HERMES_WATCHDOG_ADMIN_TOKEN
    if (-not $baseUri -or [string]::IsNullOrWhiteSpace($adminToken)) {
        return $false
    }
    try {
        Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$baseUri/api/v1/stop" `
            -Headers @{ Authorization = "Bearer $adminToken" } -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        Write-Verbose "Graceful Go watchdog stop request failed: $($_.Exception.Message)"
        return $false
    }
}

function Stop-GoWatchdog {
    param(
        [switch]$Graceful,
        [int]$TimeoutSec = 15
    )
    $watchdogPid = Get-GoWatchdogPid
    if ($watchdogPid) {
        if ($Graceful -and (Request-GoWatchdogStop)) {
            if (Wait-GoWatchdogExit -ProcessId $watchdogPid -TimeoutSec $TimeoutSec) {
                $watchdogPid = $null
            }
        }
        if ($watchdogPid -and (Get-Process -Id $watchdogPid -ErrorAction SilentlyContinue)) {
            Stop-Process -Id $watchdogPid -Force -ErrorAction SilentlyContinue
            if (-not (Wait-GoWatchdogExit -ProcessId $watchdogPid -TimeoutSec $TimeoutSec)) {
                throw "Timed out stopping Go watchdog pid $watchdogPid"
            }
        }
    }
    # The lock prevents the normal duplicate case. Reap only leftover binaries
    # after that lock owner is gone; this never terminates Hermes.exe or serve.
    Get-Process -Name hermes-watchdog -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    if (Test-GoWatchdogAlive) {
        throw "Go watchdog remains alive after stop request"
    }
    Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
}

function Stop-PsDesktopBackendWatchdog {
    # PS and Go watchdogs use different lock files — running both causes dual
    # Hermes.exe relaunch loops. Prefer Go; stop the legacy PS mutual watchdog.
    $psLock = Join-Path $HermesHome "logs\desktop-backend-watchdog.lock"
    if (Test-Path -LiteralPath $psLock) {
        try {
            $obj = Get-Content -LiteralPath $psLock -Raw | ConvertFrom-Json
            if ($obj.pid) {
                Stop-Process -Id ([int]$obj.pid) -Force -ErrorAction SilentlyContinue
            }
        } catch {}
        Remove-Item -LiteralPath $psLock -Force -ErrorAction SilentlyContinue
    }
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'Start-HermesDesktopBackendWatchdog\.ps1'
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Install-GoWatchdogCandidate {
    param(
        [string]$Candidate,
        [string]$Target
    )
    if (-not (Test-Path -LiteralPath $Candidate)) {
        throw "Missing watchdog candidate: $Candidate"
    }
    $targetDir = Split-Path -Parent $Target
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    if (-not (Test-Path -LiteralPath $Target)) {
        Move-Item -LiteralPath $Candidate -Destination $Target
        return $null
    }
    $stamp = Get-Date -Format "yyyyMMddHHmmss"
    $backup = Join-Path $targetDir ("hermes-watchdog.previous.{0}.exe" -f $stamp)
    [System.IO.File]::Replace($Candidate, $Target, $backup, $true)
    return $backup
}

function Restore-GoWatchdogBackup {
    param(
        [string]$Target,
        [string]$Backup
    )
    if (-not $Backup -or -not (Test-Path -LiteralPath $Backup)) {
        return $false
    }
    $targetDir = Split-Path -Parent $Target
    $stamp = Get-Date -Format "yyyyMMddHHmmss"
    if (Test-Path -LiteralPath $Target) {
        $failed = Join-Path $targetDir ("hermes-watchdog.failed.{0}.exe" -f $stamp)
        [System.IO.File]::Replace($Backup, $Target, $failed, $true)
    } else {
        Move-Item -LiteralPath $Backup -Destination $Target
    }
    return $true
}

function Format-WatchdogArg([string]$Name, [string]$Value) {
    if ($null -eq $Value) { $Value = "" }
    if ($Value -match '[\s"]') {
        $escaped = $Value.Replace('"', '\"')
        return ('{0}="{1}"' -f $Name, $escaped)
    }
    return ('{0}={1}' -f $Name, $Value)
}

function Get-WatchdogArgs {
    $watchdogArgs = @(
        "-interval=$IntervalSec",
        "-fail-threshold=$FailThreshold",
        "-hermes-root", $RepoRoot,
        "-hermes-home", $HermesHome,
        "-listen=$Listen"
    )
    if ($Once) { $watchdogArgs += "-once" }
    if ($NoPrewarm) { $watchdogArgs += "-prewarm-backend=false" }
    if ($ManageDesktop) { $watchdogArgs += "-manage-desktop" }
    if ($ManagedBackendPort -gt 0) { $watchdogArgs += "-managed-backend-port=$ManagedBackendPort" }
    if (-not $NoTsnet -and ($env:HERMES_WATCHDOG_TS_AUTHKEY -or $env:TS_AUTHKEY)) {
        $watchdogArgs += "-tsnet"
    }
    return $watchdogArgs
}

function Start-GoWatchdog {
    param([string]$TargetExe)
    $argList = Get-WatchdogArgs
    $workDir = Split-Path -Parent $TargetExe
    Write-Host "Starting Go watchdog detached: $TargetExe $($argList -join ' ')"

    $launched = $false
    try {
        $proc = Start-Process -FilePath $TargetExe -ArgumentList $argList -WorkingDirectory $workDir -WindowStyle Hidden -PassThru
        if ($proc) { $launched = $true }
    } catch {
        Write-Warning "Start-Process ArgumentList failed: $($_.Exception.Message); trying UseShellExecute"
    }
    if (-not $launched) {
        $shellArgs = @(
            "-interval=$IntervalSec",
            "-fail-threshold=$FailThreshold",
            (Format-WatchdogArg "-hermes-root" $RepoRoot),
            (Format-WatchdogArg "-hermes-home" $HermesHome),
            "-listen=$Listen"
        )
        if ($Once) { $shellArgs += "-once" }
        if ($NoPrewarm) { $shellArgs += "-prewarm-backend=false" }
        if ($ManageDesktop) { $shellArgs += "-manage-desktop" }
        if ($ManagedBackendPort -gt 0) { $shellArgs += "-managed-backend-port=$ManagedBackendPort" }
        if (-not $NoTsnet -and ($env:HERMES_WATCHDOG_TS_AUTHKEY -or $env:TS_AUTHKEY)) {
            $shellArgs += "-tsnet"
        }
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $TargetExe
        $startInfo.WorkingDirectory = $workDir
        $startInfo.Arguments = ($shellArgs -join ' ')
        $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
        $startInfo.UseShellExecute = $true
        [void][System.Diagnostics.Process]::Start($startInfo)
        $launched = $true
    }
    return $launched
}

function Test-GoWatchdogHealth {
    param([int]$TimeoutSec)
    $baseUri = Get-LocalWatchdogBaseUri -ListenAddress $Listen
    if (-not $baseUri) {
        return (Test-GoWatchdogAlive)
    }
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "$baseUri/health" -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {}
        Start-Sleep -Milliseconds 250
    }
    return $false
}

if ($HotSwap -and $Once) {
    throw "-HotSwap cannot be combined with -Once"
}

$didSwap = $false
$backupExe = $null
if ($HotSwap) {
    $buildScript = Join-Path $ScriptDir "Build-HermesGoWatchdog.ps1"
    Invoke-GoWatchdogBuildBounded -BuildScript $buildScript -TimeoutSec $BuildTimeoutSec `
        -OutputName (Split-Path -Leaf $CandidateExe) -SkipTest:(-not $RunBuildTests)
    if (-not (Test-Path -LiteralPath $CandidateExe)) {
        throw "Build finished but missing watchdog candidate: $CandidateExe"
    }
    Stop-GoWatchdog -Graceful -TimeoutSec $HotSwapTimeoutSec
    $backupExe = Install-GoWatchdogCandidate -Candidate $CandidateExe -Target $Exe
    $didSwap = $true
} elseif (-not (Test-Path -LiteralPath $Exe)) {
    if ($BuildIfMissing) {
        $buildScript = Join-Path $ScriptDir "Build-HermesGoWatchdog.ps1"
        try {
            Invoke-GoWatchdogBuildBounded -BuildScript $buildScript -TimeoutSec $BuildTimeoutSec `
                -OutputName (Split-Path -Leaf $Exe) -SkipTest:(-not $RunBuildTests)
        } catch {
            Write-Warning $_.Exception.Message
            Write-Warning "Skipping Go watchdog start — run Build-HermesGoWatchdog.ps1 manually when ready."
            exit 0
        }
        if (-not (Test-Path -LiteralPath $Exe)) {
            Write-Warning "Build finished but missing $Exe — skipping Go watchdog start."
            exit 0
        }
    } else {
        throw "Missing $Exe — run Build-HermesGoWatchdog.ps1 first or pass -BuildIfMissing"
    }
}

Stop-PsDesktopBackendWatchdog

if (-not $HotSwap) {
    if ($ForceRestart -or $Once) {
        Stop-GoWatchdog -Graceful -TimeoutSec $HotSwapTimeoutSec
    } elseif (Test-GoWatchdogAlive) {
        Write-Host "Go watchdog already running (lock=$LockPath)"
        exit 0
    }
}

$env:HERMES_HOME = $HermesHome
if (-not (Start-GoWatchdog -TargetExe $Exe)) {
    if ($didSwap -and (Restore-GoWatchdogBackup -Target $Exe -Backup $backupExe)) {
        [void](Start-GoWatchdog -TargetExe $Exe)
    }
    throw "Failed to start Go watchdog"
}

if (-not $Once -and -not (Test-GoWatchdogHealth -TimeoutSec $HotSwapTimeoutSec)) {
	# The candidate executable is still mapped by its process on Windows. Stop it
	# before replacing the file with the retained binary.
	Stop-GoWatchdog -Graceful -TimeoutSec $HotSwapTimeoutSec
	if ($didSwap -and (Restore-GoWatchdogBackup -Target $Exe -Backup $backupExe)) {
		[void](Start-GoWatchdog -TargetExe $Exe)
	}
    throw "Go watchdog failed its /health probe after ${HotSwapTimeoutSec}s"
}

Write-Host "Go watchdog launched (logs: $(Join-Path $HermesHome 'logs\hermes-go-watchdog.log'))"
