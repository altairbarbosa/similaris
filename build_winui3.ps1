param(
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Release',

    [string]$Version = '',

    [switch]$SkipPythonCore,

    [switch]$Package
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$winuiProject = Join-Path $projectRoot 'src\Similaris.WinUI\Similaris.WinUI.csproj'

if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw 'dotnet was not found. Install the .NET SDK and Visual Studio workloads for Windows App SDK.'
}

$dotnetInfo = dotnet --info
if ($dotnetInfo -match 'No SDKs were found') {
    throw 'No .NET SDK is installed. Install the .NET SDK and the Windows App SDK workload before building WinUI.'
}

if (-not $SkipPythonCore) {
    $previousCi = $env:CI
    $env:CI = 'true'
    try {
        & (Join-Path $projectRoot 'build_python_core.bat')
        if ($LASTEXITCODE -ne 0) {
            throw "build_python_core.bat failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        $env:CI = $previousCi
    }
}

if ($Package) {
    & dotnet restore $winuiProject
    if ($LASTEXITCODE -ne 0) {
        throw "dotnet restore failed with exit code $LASTEXITCODE."
    }

    $nugetRoot = if ($env:NUGET_PACKAGES) { $env:NUGET_PACKAGES } else { Join-Path $env:USERPROFILE '.nuget\packages' }
    $permissionsDll = Join-Path $nugetRoot 'system.security.permissions\8.0.0\lib\net8.0\System.Security.Permissions.dll'
    $msixTaskDirectory = Join-Path $nugetRoot 'microsoft.windows.sdk.buildtools.msix\1.7.251221100\tools\net6.0'
    if ((Test-Path $permissionsDll) -and (Test-Path $msixTaskDirectory)) {
        Copy-Item -LiteralPath $permissionsDll -Destination $msixTaskDirectory -Force
    }
}

$arguments = @(
    'publish',
    $winuiProject,
    '--configuration', $Configuration,
    '--runtime', 'win-x64',
    '--self-contained', 'false'
)

if (-not [string]::IsNullOrWhiteSpace($Version)) {
    $arguments += @(
        ('/p:Version=' + $Version),
        ('/p:AssemblyVersion=' + $Version),
        ('/p:FileVersion=' + $Version)
    )
}

if ($Package) {
    $arguments += @(
        '/p:GenerateAppxPackageOnBuild=true',
        '/p:AppxPackageSigningEnabled=false'
    )
} else {
    $arguments += @('/p:WindowsPackageType=None')
}

& dotnet @arguments
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed with exit code $LASTEXITCODE."
}
