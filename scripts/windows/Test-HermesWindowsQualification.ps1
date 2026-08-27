param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\.." )).Path,
    [string]$OutputDirectory = (Join-Path $PWD "windows-qualification"),
    [string]$InstallerPath = "",
    [string]$PortablePath = "",
    [string]$PreviousInstallerPath = "",
    [string]$WorkstationEvidencePath = "",
    [ValidateSet("ci", "real_workstation")]
    [string]$Scope = "ci"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $RepoRoot).Path
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $output -Force | Out-Null
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
$gates = [ordered]@{}
$details = [ordered]@{}

function Invoke-NativeChecked {
    param([string]$FilePath, [string[]]$ArgumentList, [string]$WorkingDirectory = $root)
    Push-Location $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        if ($LASTEXITCODE -ne 0) {
            throw "$FilePath failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Invoke-QualificationGate {
    param([string]$Name, [scriptblock]$Action)
    $started = [DateTime]::UtcNow
    try {
        & $Action
        $gates[$Name] = "passed"
        $details[$Name] = [ordered]@{
            status = "passed"
            duration_ms = [int]([DateTime]::UtcNow - $started).TotalMilliseconds
        }
    } catch {
        Write-Error -ErrorAction Continue "Qualification gate ${Name} failed: $_"
        $gates[$Name] = "failed"
        $details[$Name] = [ordered]@{
            status = "failed"
            duration_ms = [int]([DateTime]::UtcNow - $started).TotalMilliseconds
            error_type = $_.Exception.GetType().Name
        }
    }
}

$previousHermesHome = [Environment]::GetEnvironmentVariable("HERMES_HOME", "Process")
$temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\')
$qualificationHome = Join-Path $temporaryRoot "Hermes Qualification Home $([guid]::NewGuid())"
New-Item -ItemType Directory -Path $qualificationHome -Force | Out-Null
[Environment]::SetEnvironmentVariable("HERMES_HOME", $qualificationHome, "Process")

try {
Invoke-QualificationGate "windows_native_paths" {
    Invoke-NativeChecked $python @("-m", "pytest", "tests/downstream/test_windows_contracts.py", "-q")
}
Invoke-QualificationGate "cli_start" {
    Invoke-NativeChecked $python @("-m", "hermes_cli.main", "--version")
}
Invoke-QualificationGate "local_provider_contract" {
    $llamaEnvironmentNames = @(
        "HERMES_LLAMA_SERVER_EXE",
        "HERMES_LLAMA_MODEL_PATH",
        "HERMES_LLAMA_FALLBACK_AUTOSTART",
        "HERMES_LLAMA_GPU_PROFILE",
        "HERMES_LLAMA_KV_PROFILE",
        "HERMES_LLAMA_SPEC_TYPE",
        "HERMES_LLAMA_HOST",
        "HERMES_LLAMA_PORT",
        "HERMES_LLAMA_CONTEXT_SIZE",
        "HERMES_LLAMA_WAIT_SECONDS",
        "HERMES_LLAMA_SPEC_DRAFT_N_MAX",
        "HERMES_LLAMA_SPEC_DRAFT_P_MIN"
    )
    $savedLlamaEnvironment = @{}
    foreach ($name in $llamaEnvironmentNames) {
        $savedLlamaEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
        [Environment]::SetEnvironmentVariable($name, $null, "Process")
    }
    try {
        Invoke-NativeChecked $python @(
            "-m", "pytest", "tests/hermes_cli/test_llama_fallback_runtime.py", "-q"
        )
    } finally {
        foreach ($name in $llamaEnvironmentNames) {
            [Environment]::SetEnvironmentVariable(
                $name,
                $savedLlamaEnvironment[$name],
                "Process"
            )
        }
    }
}
Invoke-QualificationGate "upstream_api_compat" {
    Invoke-NativeChecked $python @(
        "-m", "pytest", "tests/downstream/test_upstream_api_contracts.py", "-q"
    )
}
Invoke-QualificationGate "windows_regression" {
    Invoke-NativeChecked $python @(
        "-m", "pytest",
        "tests/downstream/test_windows_contracts.py",
        "tests/downstream/test_ci_contracts.py",
        "tests/downstream/test_repository_identity.py",
        "-q"
    )
}
Invoke-QualificationGate "updater_contract" {
    Invoke-NativeChecked $python @(
        "-m", "pytest",
        "tests/hermes_cli/test_downstream_update_authority.py",
        "tests/hermes_cli/test_update_zip_fallback_guards.py",
        "-q"
    )
}
Invoke-QualificationGate "session_persistence" {
    Invoke-NativeChecked $python @("-m", "pytest", "tests/hermes_state/test_reasoning_roundtrip.py", "-q")
}
Invoke-QualificationGate "release_metadata" {
    Invoke-NativeChecked $python @(
        "-m", "pytest",
        "tests/downstream/test_distribution_metadata.py",
        "tests/downstream/test_windows_release_manifest.py",
        "-q"
    )
}
Invoke-QualificationGate "security" {
    Invoke-NativeChecked $python @(
        "-m", "pytest",
        "tests/hermes_cli/test_update_zip_symlink_reject.py",
        "tests/hermes_cli/test_update_self_lock.py",
        "-q"
    )
}
Invoke-QualificationGate "install_source" {
    Invoke-NativeChecked "powershell.exe" @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        (Join-Path $root "scripts\install.ps1"), "-ShowResolvedPaths"
    )
}
Invoke-QualificationGate "desktop_build" {
    Invoke-NativeChecked "npm" @("--workspace", "apps/desktop", "run", "typecheck")
    Invoke-NativeChecked "npm" @(
        "--workspace", "apps/desktop", "run", "test:desktop:platforms", "--",
        "electron/distribution.test.ts", "electron/bootstrap-runner.test.ts"
    )
    Invoke-NativeChecked "npm" @("--workspace", "apps/desktop", "run", "build")
}
Invoke-QualificationGate "watchdog" {
    Invoke-NativeChecked "go" @("test", "./...") (Join-Path $root "scripts\windows\watchdog-go")
}

if ($InstallerPath) {
    Invoke-QualificationGate "install_e2e" {
        Invoke-NativeChecked "powershell.exe" @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            (Join-Path $root "scripts\windows\Test-HermesInstallerE2E.ps1"),
            "-InstallerPath", $InstallerPath,
            "-OutputPath", (Join-Path $output "installer-e2e.json")
        )
    }
} else {
    $gates["install_e2e"] = "not_run"
    $details["install_e2e"] = [ordered]@{ status = "not_run" }
}

if ($PortablePath) {
    Invoke-QualificationGate "portable_e2e" {
        Invoke-NativeChecked "powershell.exe" @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            (Join-Path $root "scripts\windows\Test-HermesPortableE2E.ps1"),
            "-PortableArchive", $PortablePath,
            "-OutputPath", (Join-Path $output "portable-e2e.json")
        )
    }
} else {
    $gates["portable_e2e"] = "not_run"
    $details["portable_e2e"] = [ordered]@{ status = "not_run" }
}

if ($PreviousInstallerPath -and $InstallerPath) {
    Invoke-QualificationGate "upgrade_e2e" {
        Invoke-NativeChecked "powershell.exe" @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            (Join-Path $root "scripts\windows\Test-HermesUpgradeE2E.ps1"),
            "-PreviousInstaller", $PreviousInstallerPath,
            "-CurrentInstaller", $InstallerPath,
            "-OutputPath", (Join-Path $output "upgrade-e2e.json")
        )
    }
} else {
    $gates["upgrade_e2e"] = "not_run"
    $details["upgrade_e2e"] = [ordered]@{ status = "not_run" }
}

$gates["windows_native_python"] = if (
    $gates.windows_native_paths -eq "passed" -and
    $gates.cli_start -eq "passed" -and
    $gates.local_provider_contract -eq "passed" -and
    $gates.upstream_api_compat -eq "passed" -and
    $gates.windows_regression -eq "passed" -and
    $gates.updater_contract -eq "passed" -and
    $gates.session_persistence -eq "passed"
) { "passed" } else { "failed" }
$gates["windows_native_desktop"] = $gates.desktop_build
$gates["watchdog_go"] = $gates.watchdog
$gates["security_lock"] = $gates.security
$gates["security_locks"] = $gates.security

if ($Scope -eq "real_workstation") {
    if ($WorkstationEvidencePath) {
        $workstationEvidence = Get-Content -LiteralPath $WorkstationEvidencePath -Raw | ConvertFrom-Json
        $gates["real_workstation_evidence"] = if ($workstationEvidence.status -eq "passed") {
            "passed"
        } else {
            "failed"
        }
        $details["real_workstation_evidence"] = [ordered]@{
            status = $gates.real_workstation_evidence
            schema_version = $workstationEvidence.schema_version
        }
    } else {
        $gates["real_workstation_evidence"] = "not_run"
        $details["real_workstation_evidence"] = [ordered]@{ status = "not_run" }
    }
}

$required = @(
    "install_e2e", "portable_e2e", "upgrade_e2e", "windows_native_python",
    "windows_native_desktop", "watchdog_go", "upstream_api_compat",
    "windows_regression", "security_locks"
)
if ($Scope -eq "real_workstation") {
    $required += "real_workstation_evidence"
}
$status = if (@($required | Where-Object { $gates[$_] -ne "passed" }).Count -eq 0) {
    "passed"
} else {
    "failed"
}
$downstreamSha = (& git -C $root rev-parse HEAD).Trim()
$distribution = Get-Content -LiteralPath (Join-Path $root "downstream\distribution.json") -Raw | ConvertFrom-Json
$executedInCi = ($env:GITHUB_ACTIONS -eq "true")
$report = [ordered]@{
    schema_version = 1
    status = $status
    scope = $Scope
    generated_at_utc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    downstream_commit_sha = $downstreamSha
    upstream_snapshot_sha = $distribution.upstream.snapshot_sha
    executed_in_ci = $executedInCi
    ci_qualified = ($executedInCi -and $Scope -eq "ci" -and $status -eq "passed")
    real_workstation_qualified = (
        $Scope -eq "real_workstation" -and
        $status -eq "passed" -and
        $gates.real_workstation_evidence -eq "passed"
    )
    gates = $gates
    details = $details
}

$jsonPath = Join-Path $output "windows-qualification.json"
$summaryPath = Join-Path $output "windows-qualification.md"
[System.IO.File]::WriteAllText(
    $jsonPath,
    (($report | ConvertTo-Json -Depth 8) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false)
)
$summary = @(
    "# Windows qualification",
    "",
    "Status: $status",
    "Scope: $Scope",
    "Downstream commit: $downstreamSha",
    "Frozen upstream snapshot: $($distribution.upstream.snapshot_sha)",
    "",
    "| Gate | Result |",
    "| --- | --- |"
)
foreach ($name in $gates.Keys) {
    $summary += "| $name | $($gates[$name]) |"
}
[System.IO.File]::WriteAllText(
    $summaryPath,
    (($summary -join [Environment]::NewLine) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false)
)
$report | ConvertTo-Json -Depth 8
if ($status -ne "passed") {
    throw "Windows qualification failed"
}
} finally {
    [Environment]::SetEnvironmentVariable("HERMES_HOME", $previousHermesHome, "Process")
    $resolvedQualificationHome = [System.IO.Path]::GetFullPath($qualificationHome).TrimEnd('\')
    $qualificationParent = [System.IO.Path]::GetDirectoryName($resolvedQualificationHome)
    $qualificationLeaf = [System.IO.Path]::GetFileName($resolvedQualificationHome)
    if (
        $qualificationParent.Equals($temporaryRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
        $qualificationLeaf -match '^Hermes Qualification Home [0-9a-f-]+$' -and
        (Test-Path -LiteralPath $resolvedQualificationHome)
    ) {
        Remove-Item -LiteralPath $resolvedQualificationHome -Recurse -Force
    }
}
