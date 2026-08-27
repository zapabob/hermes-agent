param(
    [Parameter(Mandatory = $true)]
    [string]$PortableArchive,
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "HermesArtifactE2E.ps1")

$archive = (Resolve-Path -LiteralPath $PortableArchive).Path
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) "Hermes Portable E2E $([guid]::NewGuid())"
$extractRoot = Join-Path $testRoot "Extracted Product"
$profileRoot = Join-Path $testRoot "Profile With Spaces"
$previousHome = $env:HERMES_HOME

try {
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $profileRoot -Force | Out-Null
    Expand-Archive -LiteralPath $archive -DestinationPath $extractRoot -Force
    $desktop = Get-ChildItem -LiteralPath $extractRoot -Filter "Hermes.exe" -File -Recurse |
        Select-Object -First 1
    if (-not $desktop) {
        throw "Portable archive does not contain Hermes.exe"
    }
    $resourceRoot = Join-Path $desktop.Directory.FullName "resources"
    if (-not (Test-Path -LiteralPath (Join-Path $resourceRoot "app.asar"))) {
        throw "Portable archive is missing resources\app.asar"
    }
    $metadataPath = Join-Path $resourceRoot "distribution\distribution.json"
    if (-not (Test-Path -LiteralPath $metadataPath)) {
        throw "Portable archive is missing distribution metadata"
    }
    $identity = Get-HermesArtifactIdentity -DesktopPath $desktop.FullName -MetadataPath $metadataPath
    $env:HERMES_HOME = $profileRoot
    $smoke = Invoke-HermesDesktopSmoke -DesktopPath $desktop.FullName -ProfileRoot $profileRoot
    $report = [ordered]@{
        schema_version = 1
        status = "passed"
        artifact = [System.IO.Path]::GetFileName($archive)
        path_with_spaces = $true
        identity = $identity
        desktop_smoke = $smoke
        developer_checkout_required = $false
    }
    Write-HermesE2EReport -Report $report -OutputPath $OutputPath
} finally {
    $env:HERMES_HOME = $previousHome
    Remove-SafeQualificationDirectory -Path $testRoot
}
