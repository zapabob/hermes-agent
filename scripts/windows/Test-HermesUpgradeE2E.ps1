param(
    [Parameter(Mandatory = $true)]
    [string]$PreviousInstaller,
    [Parameter(Mandatory = $true)]
    [string]$CurrentInstaller,
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "HermesArtifactE2E.ps1")

$previous = (Resolve-Path -LiteralPath $PreviousInstaller).Path
$current = (Resolve-Path -LiteralPath $CurrentInstaller).Path
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) "Hermes Upgrade E2E $([guid]::NewGuid())"
$installRoot = Join-Path $testRoot "Installed Product"
$profileRoot = Join-Path $testRoot "Persistent Profile"
$sentinel = Join-Path $profileRoot "upgrade-user-data-sentinel.txt"
$previousHome = $env:HERMES_HOME

try {
    New-Item -ItemType Directory -Path $profileRoot -Force | Out-Null
    $env:HERMES_HOME = $profileRoot
    $firstExitCode = Invoke-HermesNativeProcess -FilePath $previous -ArgumentList @("/S", "/D=$installRoot")
    if ($firstExitCode -ne 0) {
        throw "Previous installer failed with exit code $firstExitCode"
    }
    [System.IO.File]::WriteAllText($sentinel, "preserve", [System.Text.UTF8Encoding]::new($false))
    $secondExitCode = Invoke-HermesNativeProcess -FilePath $current -ArgumentList @("/S")
    if ($secondExitCode -ne 0) {
        throw "Current installer failed with exit code $secondExitCode"
    }
    if (-not (Test-Path -LiteralPath $sentinel)) {
        throw "Upgrade removed profile data"
    }
    $desktop = Get-ChildItem -LiteralPath $installRoot -Filter "Hermes.exe" -File -Recurse |
        Select-Object -First 1
    if (-not $desktop) {
        throw "Upgraded product does not contain Hermes.exe"
    }
    $metadataPath = Join-Path $desktop.Directory.FullName "resources\distribution\distribution.json"
    if (-not (Test-Path -LiteralPath $metadataPath)) {
        throw "Upgraded product is missing distribution metadata"
    }
    $identity = Get-HermesArtifactIdentity -DesktopPath $desktop.FullName -MetadataPath $metadataPath
    $smoke = Invoke-HermesDesktopSmoke -DesktopPath $desktop.FullName -ProfileRoot $profileRoot
    $report = [ordered]@{
        schema_version = 1
        status = "passed"
        previous_artifact = [System.IO.Path]::GetFileName($previous)
        current_artifact = [System.IO.Path]::GetFileName($current)
        profile_data_preserved = $true
        identity = $identity
        desktop_smoke = $smoke
    }
    Write-HermesE2EReport -Report $report -OutputPath $OutputPath
} finally {
    $uninstaller = Get-ChildItem -LiteralPath $installRoot -Filter "Uninstall*.exe" -File -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($uninstaller) {
        Invoke-HermesNativeProcess -FilePath $uninstaller.FullName -ArgumentList @("/S") | Out-Null
    }
    Stop-HermesArtifactProcesses -RootPath $installRoot
    $env:HERMES_HOME = $previousHome
    Remove-SafeQualificationDirectory -Path $testRoot
}
