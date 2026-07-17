<#
.SYNOPSIS
    Builds the standalone OpenLP (NCSDA/Noir) Windows package end to end.

.DESCRIPTION
    Runs the full packaging pipeline from the repository root:
      1. Compiles Qt translations (resources/i18n/*.ts -> build/i18n/*.qm)
      2. Builds the PyInstaller bundle (packaging/OpenLP.spec -> dist/OpenLP/)
      3. Compiles the Inno Setup installer (-> dist/installer/OpenLP-Noir-<version>-setup.exe)

    The application version is read from openlp/.version and passed through to
    the installer, so the setup filename always matches the built code.

.PARAMETER SkipInstaller
    Stop after the PyInstaller bundle; do not compile the Inno Setup installer.

.PARAMETER Clean
    Pass --clean to PyInstaller to discard its build cache first.

.EXAMPLE
    .\packaging\build.ps1
    .\packaging\build.ps1 -Clean
    .\packaging\build.ps1 -SkipInstaller
#>
[CmdletBinding()]
param(
    [switch]$SkipInstaller,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed (exit code $LASTEXITCODE)."
    }
}

# --- Preflight -------------------------------------------------------------
$pyinstaller = Join-Path $root 'venv\Scripts\pyinstaller.exe'
$lrelease = Join-Path $root 'venv\Scripts\pyside6-lrelease.exe'
$iscc = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$versionFile = Join-Path $root 'openlp\.version'

foreach ($tool in @($pyinstaller, $lrelease)) {
    if (-not (Test-Path $tool)) {
        throw "Not found: $tool. Activate/create the venv and 'pip install pyinstaller pyside6'."
    }
}
if (-not (Test-Path $versionFile)) {
    throw "Not found: $versionFile. The frozen app reads its version from this file."
}
$version = (Get-Content $versionFile -TotalCount 1).Trim()
Write-Host "Packaging OpenLP NCSDA/Noir version $version" -ForegroundColor Green

# --- 1. Translations -------------------------------------------------------
$i18nSrc = Join-Path $root 'resources\i18n'
$i18nOut = Join-Path $root 'build\i18n'
New-Item -ItemType Directory -Force $i18nOut | Out-Null
$tsFiles = Get-ChildItem (Join-Path $i18nSrc '*.ts')
Invoke-Step "Compiling $($tsFiles.Count) translation files" {
    foreach ($ts in $tsFiles) {
        $qm = Join-Path $i18nOut ($ts.BaseName + '.qm')
        & $lrelease $ts.FullName -qm $qm -silent
        if ($LASTEXITCODE -ne 0) { break }
    }
}

# --- 2. PyInstaller bundle -------------------------------------------------
$pyiArgs = @('--noconfirm')
if ($Clean) { $pyiArgs += '--clean' }
$pyiArgs += (Join-Path $root 'packaging\OpenLP.spec')
Invoke-Step 'Building PyInstaller bundle' {
    & $pyinstaller @pyiArgs
}
$bundle = Join-Path $root 'dist\OpenLP'
if (-not (Test-Path (Join-Path $bundle 'OpenLP.exe'))) {
    throw "PyInstaller reported success but $bundle\OpenLP.exe is missing."
}
$bundleMB = [math]::Round((Get-ChildItem $bundle -Recurse -File | Measure-Object Length -Sum).Sum / 1MB)
Write-Host "Bundle: $bundle ($bundleMB MB)" -ForegroundColor Green

# --- 3. Inno Setup installer -----------------------------------------------
if ($SkipInstaller) {
    Write-Host 'Skipping installer (-SkipInstaller).' -ForegroundColor Yellow
    return
}
if (-not (Test-Path $iscc)) {
    throw "Not found: $iscc. Install Inno Setup 6 or re-run with -SkipInstaller."
}
Invoke-Step 'Compiling Inno Setup installer' {
    & $iscc "/DMyAppVersion=$version" (Join-Path $root 'packaging\installer.iss')
}
$setup = Get-ChildItem (Join-Path $root 'dist\installer\*-setup.exe') |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
$setupMB = [math]::Round($setup.Length / 1MB)
Write-Host "Installer: $($setup.FullName) ($setupMB MB)" -ForegroundColor Green
