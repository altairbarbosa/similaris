param(
    [Parameter(Mandatory = $false)]
    [ValidatePattern('^\d+\.\d+\.\d+\.\d+$')]
    [string]$Version = '0.1.0.0',

    [Parameter(Mandatory = $false)]
    [string]$ExecutablePath = 'dist\Similaris.exe',

    [Parameter(Mandatory = $false)]
    [string]$OutputDirectory = 'dist'
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

if (-not (Test-Path $executable -PathType Leaf)) {
    throw "Windows executable not found: $executable. Run build_windows.bat first."
}

$makeAppx = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin' `
    -Filter MakeAppx.exe -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\x64\\MakeAppx\.exe$' } |
    Sort-Object FullName -Descending |
    Select-Object -First 1

if (-not $makeAppx) {
    throw 'MakeAppx.exe was not found. Install the Windows 10/11 SDK.'
}

if (Test-Path $staging) {
    Remove-Item $staging -Recurse -Force
}
New-Item $staging -ItemType Directory -Force | Out-Null
New-Item (Join-Path $staging 'Assets') -ItemType Directory -Force | Out-Null
New-Item $output -ItemType Directory -Force | Out-Null

Copy-Item $executable (Join-Path $staging 'Similaris.exe')
Copy-Item (Join-Path $projectDirectory 'packaging\assets\*.png') (Join-Path $staging 'Assets')

$manifest = (Get-Content $manifestTemplate -Raw).Replace('@@VERSION@@', $Version)
[System.IO.File]::WriteAllText(
    (Join-Path $staging 'AppxManifest.xml'),
    $manifest,
    [System.Text.UTF8Encoding]::new($false)
)

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
