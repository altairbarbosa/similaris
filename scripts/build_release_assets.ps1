param(
    [string]$Version = "0.1.4.0"
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$distRoot = Join-Path $projectRoot 'dist'
$archiveName = 'Similaris-Windows-x64'
$publicAssets = Join-Path $distRoot 'release-assets'
$storeAssets = Join-Path $distRoot 'store-assets'
$stagingRoot = Join-Path $distRoot 'staging'
$portableStaging = Join-Path $stagingRoot $archiveName
$wixToolPath = Join-Path $distRoot 'tools\wix'
$wixRoot = Join-Path $distRoot 'wix'
$msiPath = Join-Path $publicAssets "$archiveName.msi"

function Normalize-Version {
    param([string]$Value)

    $clean = $Value.TrimStart('v', 'V')
    $parts = @($clean -split '[^0-9]+' | Where-Object { $_ -ne '' })
    if ($parts.Count -eq 0) {
        return '0.1.4.0'
    }
    while ($parts.Count -lt 4) {
        $parts += '0'
    }
    return ($parts[0..3] -join '.')
}

function ConvertTo-MsiVersion {
    param([string]$Value)

    $parts = @($Value -split '\.')
    return ($parts[0..2] -join '.')
}

function Set-PackageManifestVersion {
    param(
        [string]$PackageVersion
    )

    $manifestPath = Join-Path $projectRoot 'src\Similaris.WinUI\Package.appxmanifest'
    $document = [xml](Get-Content $manifestPath -Raw)
    $identity = $document.SelectSingleNode("//*[local-name()='Identity']")
    if (-not $identity) {
        throw 'Package identity was not found in Package.appxmanifest.'
    }
    $identity.Version = $PackageVersion
    $settings = [System.Xml.XmlWriterSettings]::new()
    $settings.Indent = $true
    $settings.Encoding = [System.Text.UTF8Encoding]::new($false)
    $writer = [System.Xml.XmlWriter]::Create($manifestPath, $settings)
    try {
        $document.Save($writer)
    }
    finally {
        $writer.Dispose()
    }
}

function Invoke-WithRetry {
    param(
        [scriptblock]$Action,
        [int]$Attempts = 5,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            & $Action
            return
        }
        catch {
            if ($attempt -eq $Attempts) {
                throw
            }
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

function Get-PublishDirectory {
    $publish = Get-ChildItem (Join-Path $projectRoot 'src\Similaris.WinUI\bin\Release') -Directory -Recurse |
        Where-Object { Test-Path (Join-Path $_.FullName 'Similaris.WinUI.exe') } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if (-not $publish) {
        throw 'WinUI publish output was not found.'
    }
    return $publish.FullName
}

function New-StableGuid {
    param([string]$Seed)

    $md5 = [System.Security.Cryptography.MD5]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Seed.ToLowerInvariant())
    try {
        return [Guid]::new($md5.ComputeHash($bytes)).ToString().ToUpperInvariant()
    }
    finally {
        $md5.Dispose()
    }
}

function New-WixId {
    param(
        [string]$Prefix,
        [string]$Seed
    )

    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Seed.ToLowerInvariant())
    try {
        $hashBytes = $sha.ComputeHash($bytes)
        $hash = -join ($hashBytes | ForEach-Object { $_.ToString('X2') })
        $hash = $hash.Substring(0, 24)
        return "$Prefix$hash"
    }
    finally {
        $sha.Dispose()
    }
}

function Get-RelativePath {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    $baseFullPath = [System.IO.Path]::GetFullPath($BasePath).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $targetFullPath = [System.IO.Path]::GetFullPath($TargetPath)
    $baseUri = [Uri]::new($baseFullPath)
    $targetUri = [Uri]::new($targetFullPath)
    return [Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace('/', [System.IO.Path]::DirectorySeparatorChar)
}

function Add-DirectoryXml {
    param(
        [System.Xml.XmlWriter]$Writer,
        [System.IO.DirectoryInfo]$Directory,
        [string]$PublishDirectory,
        [System.Collections.Generic.List[string]]$ComponentIds
    )

    foreach ($file in Get-ChildItem $Directory.FullName -File | Sort-Object Name) {
        $relative = Get-RelativePath -BasePath $PublishDirectory -TargetPath $file.FullName
        $componentId = New-WixId 'cmp_' $relative
        $componentGuid = New-StableGuid "component:$relative"
        $ComponentIds.Add($componentId)

        $Writer.WriteStartElement('Component')
        $Writer.WriteAttributeString('Id', $componentId)
        $Writer.WriteAttributeString('Guid', "{$componentGuid}")
        $Writer.WriteStartElement('File')
        $Writer.WriteAttributeString('Id', (New-WixId 'fil_' $relative))
        $Writer.WriteAttributeString('Source', $file.FullName)
        $Writer.WriteAttributeString('KeyPath', 'yes')
        $Writer.WriteEndElement()
        $Writer.WriteEndElement()
    }

    foreach ($child in Get-ChildItem $Directory.FullName -Directory | Sort-Object Name) {
        $relative = Get-RelativePath -BasePath $PublishDirectory -TargetPath $child.FullName
        $Writer.WriteStartElement('Directory')
        $Writer.WriteAttributeString('Id', (New-WixId 'dir_' $relative))
        $Writer.WriteAttributeString('Name', $child.Name)
        Add-DirectoryXml -Writer $Writer -Directory $child -PublishDirectory $PublishDirectory -ComponentIds $ComponentIds
        $Writer.WriteEndElement()
    }
}

function New-WixSource {
    param(
        [string]$PublishDirectory,
        [string]$OutputPath,
        [string]$PackageVersion
    )

    $componentIds = [System.Collections.Generic.List[string]]::new()
    $settings = [System.Xml.XmlWriterSettings]::new()
    $settings.Indent = $true
    $settings.Encoding = [System.Text.UTF8Encoding]::new($false)
    $writer = [System.Xml.XmlWriter]::Create($OutputPath, $settings)
    try {
        $writer.WriteStartDocument()
        $writer.WriteStartElement('Wix', 'http://wixtoolset.org/schemas/v4/wxs')
        $writer.WriteStartElement('Package')
        $writer.WriteAttributeString('Name', 'Similaris')
        $writer.WriteAttributeString('Manufacturer', 'Altair Barbosa')
        $writer.WriteAttributeString('Version', $PackageVersion)
        $writer.WriteAttributeString('UpgradeCode', '{1E856B98-C8B2-4DF2-A5C4-13D3A99A7F1E}')
        $writer.WriteAttributeString('Scope', 'perMachine')

        $writer.WriteStartElement('MajorUpgrade')
        $writer.WriteAttributeString('DowngradeErrorMessage', 'A newer version of Similaris is already installed.')
        $writer.WriteEndElement()

        $writer.WriteStartElement('MediaTemplate')
        $writer.WriteAttributeString('EmbedCab', 'yes')
        $writer.WriteEndElement()

        $writer.WriteStartElement('StandardDirectory')
        $writer.WriteAttributeString('Id', 'ProgramFiles64Folder')
        $writer.WriteStartElement('Directory')
        $writer.WriteAttributeString('Id', 'INSTALLFOLDER')
        $writer.WriteAttributeString('Name', 'Similaris')
        Add-DirectoryXml -Writer $writer -Directory ([System.IO.DirectoryInfo]::new($PublishDirectory)) -PublishDirectory $PublishDirectory -ComponentIds $componentIds
        $writer.WriteEndElement()
        $writer.WriteEndElement()

        $writer.WriteStartElement('StandardDirectory')
        $writer.WriteAttributeString('Id', 'ProgramMenuFolder')
        $writer.WriteStartElement('Directory')
        $writer.WriteAttributeString('Id', 'ApplicationProgramsFolder')
        $writer.WriteAttributeString('Name', 'Similaris')
        $writer.WriteStartElement('Component')
        $writer.WriteAttributeString('Id', 'StartMenuShortcutComponent')
        $writer.WriteAttributeString('Guid', '{B9F1ACD9-522B-438C-AAB9-0FF89F3064B5}')
        $writer.WriteStartElement('Shortcut')
        $writer.WriteAttributeString('Id', 'ApplicationStartMenuShortcut')
        $writer.WriteAttributeString('Name', 'Similaris')
        $writer.WriteAttributeString('Description', 'Similaris')
        $writer.WriteAttributeString('Target', '[INSTALLFOLDER]Similaris.WinUI.exe')
        $writer.WriteAttributeString('WorkingDirectory', 'INSTALLFOLDER')
        $writer.WriteEndElement()
        $writer.WriteStartElement('RemoveFolder')
        $writer.WriteAttributeString('Id', 'ApplicationProgramsFolder')
        $writer.WriteAttributeString('On', 'uninstall')
        $writer.WriteEndElement()
        $writer.WriteStartElement('RegistryValue')
        $writer.WriteAttributeString('Root', 'HKCU')
        $writer.WriteAttributeString('Key', 'Software\Similaris')
        $writer.WriteAttributeString('Name', 'installed')
        $writer.WriteAttributeString('Type', 'integer')
        $writer.WriteAttributeString('Value', '1')
        $writer.WriteAttributeString('KeyPath', 'yes')
        $writer.WriteEndElement()
        $writer.WriteEndElement()
        $writer.WriteEndElement()
        $writer.WriteEndElement()

        $writer.WriteStartElement('Feature')
        $writer.WriteAttributeString('Id', 'Main')
        $writer.WriteAttributeString('Title', 'Similaris')
        $writer.WriteAttributeString('Level', '1')
        foreach ($componentId in $componentIds) {
            $writer.WriteStartElement('ComponentRef')
            $writer.WriteAttributeString('Id', $componentId)
            $writer.WriteEndElement()
        }
        $writer.WriteStartElement('ComponentRef')
        $writer.WriteAttributeString('Id', 'StartMenuShortcutComponent')
        $writer.WriteEndElement()
        $writer.WriteEndElement()

        $writer.WriteEndElement()
        $writer.WriteEndElement()
        $writer.WriteEndDocument()
    }
    finally {
        $writer.Dispose()
    }
}

$packageVersion = Normalize-Version $Version
$msiVersion = ConvertTo-MsiVersion $packageVersion
Set-PackageManifestVersion -PackageVersion $packageVersion

& (Join-Path $projectRoot 'build_winui3.ps1') -Configuration Release -Version $packageVersion
if ($LASTEXITCODE -ne 0) {
    throw "build_winui3.ps1 failed with exit code $LASTEXITCODE."
}

$publishDirectory = Get-PublishDirectory
New-Item $publicAssets -ItemType Directory -Force | Out-Null
New-Item $storeAssets -ItemType Directory -Force | Out-Null
New-Item $wixRoot -ItemType Directory -Force | Out-Null
New-Item $stagingRoot -ItemType Directory -Force | Out-Null
Get-ChildItem $publicAssets -File -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem $storeAssets -File -ErrorAction SilentlyContinue | Remove-Item -Force
if (Test-Path $portableStaging) {
    Remove-Item -LiteralPath $portableStaging -Recurse -Force
}
New-Item $portableStaging -ItemType Directory -Force | Out-Null
Invoke-WithRetry -Action {
    Copy-Item -Path (Join-Path $publishDirectory '*') -Destination $portableStaging -Recurse -Force
}

$zipPath = Join-Path $publicAssets "$archiveName.zip"
$tarPath = Join-Path $publicAssets "$archiveName.tar.gz"
if (Test-Path $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
if (Test-Path $tarPath) { Remove-Item -LiteralPath $tarPath -Force }

Invoke-WithRetry -Action {
    Compress-Archive -Path $portableStaging -DestinationPath $zipPath -Force
}
tar -czf $tarPath -C $stagingRoot $archiveName

New-Item $wixToolPath -ItemType Directory -Force | Out-Null
$wixExe = Join-Path $wixToolPath 'wix.exe'
if (-not (Test-Path $wixExe)) {
    dotnet tool install wix --tool-path $wixToolPath --version 6.0.2
    if ($LASTEXITCODE -ne 0) {
        throw "wix tool install failed with exit code $LASTEXITCODE."
    }
}

$wixSource = Join-Path $wixRoot 'Similaris.wxs'
New-WixSource -PublishDirectory $portableStaging -OutputPath $wixSource -PackageVersion $msiVersion
& $wixExe build $wixSource -arch x64 -pdbtype none -out $msiPath
if ($LASTEXITCODE -ne 0) {
    throw "wix build failed with exit code $LASTEXITCODE."
}

& (Join-Path $projectRoot 'build_winui3.ps1') -Configuration Release -Version $packageVersion -Package -SkipPythonCore
if ($LASTEXITCODE -ne 0) {
    throw "Store package build failed with exit code $LASTEXITCODE."
}

$storePackages = Get-ChildItem (Join-Path $projectRoot 'src\Similaris.WinUI\AppPackages') -Recurse -File |
    Where-Object { $_.Extension -in '.msix', '.msixupload', '.appx', '.appxupload' }
foreach ($package in $storePackages) {
    Copy-Item -LiteralPath $package.FullName -Destination (Join-Path $storeAssets $package.Name) -Force
}

if (-not (Get-ChildItem $storeAssets -File -ErrorAction SilentlyContinue)) {
    throw 'Store package was not generated.'
}

Get-ChildItem $publicAssets, $storeAssets -File | Select-Object FullName, Length
