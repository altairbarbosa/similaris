param(
    [Parameter(Mandatory = $false)]
    [ValidatePattern('^\d+\.\d+\.\d+\.\d+$')]
    [string]$Version = '0.1.0.0',

    [Parameter(Mandatory = $false)]
    [string]$ExecutablePath = 'dist\Similaris.exe',

    [Parameter(Mandatory = $false)]
    [string]$OutputDirectory = 'dist',

    [Parameter(Mandatory = $false)]
    [string]$EnvironmentFile = '.env'
)

$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$executable = Join-Path $projectDirectory $ExecutablePath
$output = Join-Path $projectDirectory $OutputDirectory
$staging = Join-Path $projectDirectory 'build\msix-layout'
$manifestTemplate = Join-Path $projectDirectory 'packaging\AppxManifest.xml.in'
$packageName = "Similaris-Store-$Version-x64.msix"
$uploadName = "Similaris-Store-$Version-x64.msixupload"
$packagePath = Join-Path $output $packageName
$uploadPath = Join-Path $output $uploadName

function Import-EnvironmentFile {
    param([string]$Path)

    if (-not (Test-Path $Path -PathType Leaf)) {
        return
    }

    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }

        $separator = $trimmed.IndexOf('=')
        if ($separator -lt 1) {
            throw "Invalid entry in environment file: $line"
        }

        $name = $trimmed.Substring(0, $separator).Trim()
        $value = $trimmed.Substring($separator + 1).Trim()
        if (
            $value.Length -ge 2 -and
            (($value.StartsWith('"') -and $value.EndsWith('"')) -or
             ($value.StartsWith("'") -and $value.EndsWith("'")))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        if (-not [System.Environment]::GetEnvironmentVariable($name, 'Process')) {
            [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
        }
    }
}

function Get-RequiredEnvironmentValue {
    param([string]$Name)

    $value = [System.Environment]::GetEnvironmentVariable($Name, 'Process')
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Required Microsoft Store setting is missing: $Name"
    }
    return $value
}

$environmentPath = if ([System.IO.Path]::IsPathRooted($EnvironmentFile)) {
    $EnvironmentFile
} else {
    Join-Path $projectDirectory $EnvironmentFile
}
Import-EnvironmentFile $environmentPath

$storeIdentityName = Get-RequiredEnvironmentValue 'MICROSOFT_STORE_IDENTITY_NAME'
$storeIdentityPublisher = Get-RequiredEnvironmentValue 'MICROSOFT_STORE_IDENTITY_PUBLISHER'
$storePublisherDisplayName = Get-RequiredEnvironmentValue 'MICROSOFT_STORE_PUBLISHER_DISPLAY_NAME'

if (-not (Test-Path $executable -PathType Leaf)) {
    throw "Windows executable not found: $executable. Run build_windows.bat first."
}

if (Test-Path $staging) {
    Remove-Item $staging -Recurse -Force
}
New-Item $staging -ItemType Directory -Force | Out-Null
New-Item (Join-Path $staging 'Assets') -ItemType Directory -Force | Out-Null
New-Item $output -ItemType Directory -Force | Out-Null

Copy-Item $executable (Join-Path $staging 'Similaris.exe')
Copy-Item (Join-Path $projectDirectory 'packaging\assets\*.png') (Join-Path $staging 'Assets')

$manifest = (Get-Content $manifestTemplate -Raw).
    Replace('@@VERSION@@', $Version).
    Replace(
        '@@MICROSOFT_STORE_IDENTITY_NAME@@',
        [System.Security.SecurityElement]::Escape($storeIdentityName)
    ).
    Replace(
        '@@MICROSOFT_STORE_IDENTITY_PUBLISHER@@',
        [System.Security.SecurityElement]::Escape($storeIdentityPublisher)
    ).
    Replace(
        '@@MICROSOFT_STORE_PUBLISHER_DISPLAY_NAME@@',
        [System.Security.SecurityElement]::Escape($storePublisherDisplayName)
    )
if ($manifest.Contains('@@')) {
    throw 'The generated manifest contains unresolved placeholders.'
}
[System.IO.File]::WriteAllText(
    (Join-Path $staging 'AppxManifest.xml'),
    $manifest,
    [System.Text.UTF8Encoding]::new($false)
)

$makeAppx = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin' `
    -Filter MakeAppx.exe -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\x64\\MakeAppx\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1

if (-not $makeAppx) {
    throw 'MakeAppx.exe was not found. Install the Windows 10/11 SDK.'
}

Remove-Item $packagePath, $uploadPath -Force -ErrorAction SilentlyContinue
& $makeAppx.FullName pack /d $staging /p $packagePath /o
if ($LASTEXITCODE -ne 0) {
    throw "MakeAppx failed with exit code $LASTEXITCODE."
}

$uploadDirectory = Join-Path $projectDirectory 'build\msix-upload'
if (Test-Path $uploadDirectory) {
    Remove-Item $uploadDirectory -Recurse -Force
}
New-Item $uploadDirectory -ItemType Directory -Force | Out-Null
Copy-Item $packagePath (Join-Path $uploadDirectory $packageName)
$zipPath = [System.IO.Path]::ChangeExtension($uploadPath, '.zip')
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $uploadDirectory '*') -DestinationPath $zipPath
Move-Item $zipPath $uploadPath

Write-Host "Store package: $packagePath"
Write-Host "Partner Center upload: $uploadPath"
Write-Host 'The Store will sign the package after certification.'
