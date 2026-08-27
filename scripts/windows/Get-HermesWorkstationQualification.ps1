param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path,
    [string]$OutputPath = (Join-Path $PWD "workstation-qualification.json"),
    [string]$ArtifactPath = "",
    [string]$BackendEndpoint = "http://127.0.0.1:9119/api/status",
    [string]$WatchdogEndpoint = "http://127.0.0.1:9920/health",
    [string]$LlamaEndpoint = "http://127.0.0.1:8080/v1/models",
    [string]$EmbeddingEndpoint = "http://127.0.0.1:8082/health",
    [ValidateSet("passed", "failed", "not_run")]
    [string]$SleepResumeResult = "not_run",
    [ValidateSet("passed", "failed", "not_run")]
    [string]$RestartRecoveryResult = "not_run",
    [switch]$AllowIncomplete
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $RepoRoot).Path
$distribution = Get-Content -LiteralPath (Join-Path $root "downstream\distribution.json") -Raw |
    ConvertFrom-Json

function Test-LocalEndpoint {
    param([string]$Uri)
    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 5
        return [ordered]@{
            status = if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                "passed"
            } else {
                "failed"
            }
            http_status = [int]$response.StatusCode
        }
    } catch {
        return [ordered]@{
            status = "failed"
            error_type = $_.Exception.GetType().Name
        }
    }
}

$operatingSystem = Get-CimInstance Win32_OperatingSystem
$nvidiaGpu = $null
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    $gpuRows = @(& $nvidiaSmi.Source `
        --query-gpu=name,memory.total `
        --format=csv,noheader,nounits 2>$null)
    if ($LASTEXITCODE -eq 0 -and $gpuRows.Count -gt 0) {
        $parts = $gpuRows[0] -split ",", 2
        if ($parts.Count -eq 2) {
            $nvidiaGpu = [ordered]@{
                model = $parts[0].Trim()
                vram_mib = [int]$parts[1].Trim()
                source = "nvidia-smi"
            }
        }
    }
}
if (-not $nvidiaGpu) {
    $videoController = Get-CimInstance Win32_VideoController |
        Where-Object { $_.Name -match "NVIDIA" } |
        Select-Object -First 1
    if ($videoController) {
        $nvidiaGpu = [ordered]@{
            model = [string]$videoController.Name
            vram_mib = [int]([double]$videoController.AdapterRAM / 1MB)
            source = "Win32_VideoController"
        }
    }
}

$desktopProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'Hermes.exe'" -ErrorAction SilentlyContinue)
$desktopIdentities = @()
foreach ($desktopProcess in $desktopProcesses) {
    if (-not $desktopProcess.ExecutablePath -or -not (Test-Path -LiteralPath $desktopProcess.ExecutablePath)) {
        continue
    }
    $desktopVersion = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($desktopProcess.ExecutablePath)
    $desktopIdentities += [ordered]@{
        product_name = $desktopVersion.ProductName
        distribution_id = $desktopVersion.InternalName
        distribution_version = $desktopVersion.SpecialBuild
        expected_distribution = (
            $desktopVersion.ProductName -eq $distribution.display_name -and
            $desktopVersion.InternalName -eq $distribution.id -and
            $desktopVersion.SpecialBuild -eq $distribution.version
        )
    }
}
$matchingDesktopCount = @($desktopIdentities | Where-Object { $_.expected_distribution }).Count
$runtime = [ordered]@{
    desktop_launch = [ordered]@{
        status = if ($matchingDesktopCount -gt 0) { "passed" } else { "failed" }
        process_count = $desktopProcesses.Count
        matching_distribution_process_count = $matchingDesktopCount
        identities = $desktopIdentities
    }
    backend_launch = Test-LocalEndpoint $BackendEndpoint
    watchdog_state = Test-LocalEndpoint $WatchdogEndpoint
    llama_endpoint_state = Test-LocalEndpoint $LlamaEndpoint
    embedding_endpoint_state = Test-LocalEndpoint $EmbeddingEndpoint
    sleep_resume_result = $SleepResumeResult
    restart_recovery_result = $RestartRecoveryResult
}

$artifact = $null
if ($ArtifactPath) {
    $resolvedArtifact = (Resolve-Path -LiteralPath $ArtifactPath).Path
    $versionInfo = [System.Diagnostics.FileVersionInfo]::GetVersionInfo($resolvedArtifact)
    $signature = Get-AuthenticodeSignature -LiteralPath $resolvedArtifact
    $artifact = [ordered]@{
        file_name = [System.IO.Path]::GetFileName($resolvedArtifact)
        sha256 = (Get-FileHash -LiteralPath $resolvedArtifact -Algorithm SHA256).Hash.ToLowerInvariant()
        product_name = $versionInfo.ProductName
        product_version = $versionInfo.ProductVersion
        file_version = $versionInfo.FileVersion
        signature_status = [string]$signature.Status
        expected_distribution_filename = (
            [System.IO.Path]::GetFileName($resolvedArtifact).IndexOf(
                [string]$distribution.version,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        )
    }
}

$downstreamSha = (& git -C $root rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not resolve downstream commit"
}
$requiredRuntimeResults = @(
    $runtime.desktop_launch.status,
    $runtime.backend_launch.status,
    $runtime.watchdog_state.status,
    $runtime.llama_endpoint_state.status,
    $runtime.embedding_endpoint_state.status,
    $runtime.sleep_resume_result,
    $runtime.restart_recovery_result
)
$hardwareQualified = (
    [Environment]::Is64BitOperatingSystem -and
    $null -ne $nvidiaGpu -and
    $nvidiaGpu.vram_mib -gt 0
)
$artifactQualified = (
    $null -ne $artifact -and
    $artifact.expected_distribution_filename
)
$status = if (
    $hardwareQualified -and
    $artifactQualified -and
    @($requiredRuntimeResults | Where-Object { $_ -ne "passed" }).Count -eq 0
) { "passed" } else { "failed" }

$report = [ordered]@{
    schema_version = 1
    status = $status
    generated_at_utc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    platform = [ordered]@{
        windows_caption = [string]$operatingSystem.Caption
        windows_version = [string]$operatingSystem.Version
        windows_build = [string]$operatingSystem.BuildNumber
        cpu_architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        operating_system_64_bit = [Environment]::Is64BitOperatingSystem
        nvidia_gpu = $nvidiaGpu
    }
    downstream_commit_sha = $downstreamSha
    upstream_snapshot_sha = [string]$distribution.upstream.snapshot_sha
    artifact_identity = $artifact
    runtime = $runtime
    privacy = [ordered]@{
        usernames_recorded = $false
        local_paths_recorded = $false
        secrets_recorded = $false
        prompts_or_sessions_recorded = $false
    }
}

$destination = [System.IO.Path]::GetFullPath($OutputPath)
$destinationDirectory = Split-Path -Parent $destination
if ($destinationDirectory) {
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
}
[System.IO.File]::WriteAllText(
    $destination,
    (($report | ConvertTo-Json -Depth 8) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false)
)
$report | ConvertTo-Json -Depth 8
if ($status -ne "passed" -and -not $AllowIncomplete) {
    throw "Real workstation qualification failed or remains incomplete"
}
