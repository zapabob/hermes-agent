function Get-HermesArtifactIdentity {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DesktopPath,
        [Parameter(Mandatory = $true)]
        [string]$MetadataPath
    )

    $metadata = Get-Content -LiteralPath $MetadataPath -Raw | ConvertFrom-Json
    $version = (Get-Item -LiteralPath $DesktopPath).VersionInfo
    if ($version.ProductName -ne $metadata.display_name) {
        throw "Unexpected product name: $($version.ProductName)"
    }
    if ($version.InternalName -ne $metadata.id) {
        throw "Unexpected distribution id: $($version.InternalName)"
    }
    if ($version.SpecialBuild -ne $metadata.version) {
        throw "Unexpected distribution version: $($version.SpecialBuild)"
    }
    [ordered]@{
        product_name = $version.ProductName
        distribution_id = $version.InternalName
        distribution_version = $version.SpecialBuild
        windows_file_version = $version.FileVersion
    }
}

function Stop-HermesArtifactProcesses {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath
    )

    $root = [System.IO.Path]::GetFullPath($RootPath).TrimEnd('\') + '\'
    $owned = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)
    })
    if ($owned.Count -gt 0) {
        Stop-Process -Id @($owned.ProcessId) -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

function Remove-SafeQualificationDirectory {
    param([string]$Path)

    $resolved = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    $tempRoot = [System.IO.Path]::GetFullPath(
        [System.IO.Path]::GetTempPath()
    ).TrimEnd('\')
    $prefix = $tempRoot + '\'
    if (-not $resolved.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside the temporary directory: $resolved"
    }
    $parent = [System.IO.Path]::GetDirectoryName($resolved)
    if (-not $parent.Equals($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a nested qualification directory: $resolved"
    }
    $leaf = [System.IO.Path]::GetFileName($resolved)
    if ($leaf -notmatch '^Hermes (Installer|Portable|Upgrade) E2E [0-9a-f-]+$') {
        throw "Refusing to remove an unexpected qualification directory: $resolved"
    }
    if (Test-Path -LiteralPath $resolved) {
        foreach ($attempt in 1..30) {
            try {
                Remove-Item -LiteralPath $resolved -Recurse -Force
                break
            } catch {
                if ($attempt -eq 30) { throw }
                Start-Sleep -Seconds 1
            }
        }
    }
}

function Invoke-HermesDesktopSmoke {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DesktopPath,
        [Parameter(Mandatory = $true)]
        [string]$ProfileRoot
    )

    $desktop = (Resolve-Path -LiteralPath $DesktopPath).Path
    $workingDirectory = Split-Path -Parent $desktop
    $electronProfile = Join-Path $ProfileRoot "Electron Profile"
    New-Item -ItemType Directory -Path $electronProfile -Force | Out-Null
    $process = Start-Process -FilePath $desktop -ArgumentList @("--user-data-dir=$electronProfile") `
        -WorkingDirectory $workingDirectory -PassThru -WindowStyle Hidden
    try {
        Start-Sleep -Seconds 8
        $owned = @(Get-CimInstance Win32_Process -Filter "Name = 'Hermes.exe'" -ErrorAction Stop |
            Where-Object { $_.ExecutablePath -eq $desktop })
        if ($owned.Count -eq 0) {
            $exit = if ($process.HasExited) { $process.ExitCode } else { "unknown" }
            throw "Hermes desktop did not remain running during smoke test; exit=$exit"
        }
        [ordered]@{
            started_process_id = $process.Id
            observed_process_count = $owned.Count
            observation_seconds = 8
        }
    } finally {
        Stop-HermesArtifactProcesses -RootPath $workingDirectory
    }
}

function Invoke-HermesNativeProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$ArgumentList = @()
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $FilePath
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.Arguments = (@($ArgumentList | ForEach-Object {
        if ($_ -match '[\s"]') {
            '"' + $_.Replace('"', '\"') + '"'
        } else {
            $_
        }
    }) -join ' ')
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $process.WaitForExit()
    $process.ExitCode
}

function Write-HermesE2EReport {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Report,
        [string]$OutputPath = ""
    )

    $json = ($Report | ConvertTo-Json -Depth 6)
    if ($OutputPath) {
        $fullPath = [System.IO.Path]::GetFullPath($OutputPath)
        $parent = Split-Path -Parent $fullPath
        if ($parent) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        [System.IO.File]::WriteAllText(
            $fullPath,
            ($json + [Environment]::NewLine),
            [System.Text.UTF8Encoding]::new($false)
        )
    }
    $json
}
