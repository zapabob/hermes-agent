param(
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath,
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "HermesArtifactE2E.ps1")

$installer = (Resolve-Path -LiteralPath $InstallerPath).Path
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) "Hermes Installer E2E $([guid]::NewGuid())"
$installRoot = Join-Path $testRoot "Installed Product"
$profileRoot = Join-Path $testRoot "Profile With Spaces"
$previousHome = $env:HERMES_HOME

try {
    New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $profileRoot -Force | Out-Null
    $env:HERMES_HOME = $profileRoot
    $installExitCode = Invoke-HermesNativeProcess -FilePath $installer -ArgumentList @("/S", "/D=$installRoot")
    if ($installExitCode -ne 0) {
        throw "NSIS installer failed with exit code $installExitCode"
    }
    $desktop = Get-ChildItem -LiteralPath $installRoot -Filter "Hermes.exe" -File -Recurse |
        Select-Object -First 1
    if (-not $desktop) {
        throw "Installed product does not contain Hermes.exe"
    }
    $metadataPath = Join-Path $desktop.Directory.FullName "resources\distribution\distribution.json"
    if (-not (Test-Path -LiteralPath $metadataPath)) {
        throw "Installed product is missing distribution metadata"
    }
    $identity = Get-HermesArtifactIdentity -DesktopPath $desktop.FullName -MetadataPath $metadataPath
    $smoke = Invoke-HermesDesktopSmoke -DesktopPath $desktop.FullName -ProfileRoot $profileRoot
    $report = [ordered]@{
        schema_version = 1
        status = "passed"
        artifact = [System.IO.Path]::GetFileName($installer)
        non_admin_install = $true
        path_with_spaces = $true
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
