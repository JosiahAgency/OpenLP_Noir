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
$buildStopwatch = [System.Diagnostics.Stopwatch]::StartNew()

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "==> $Name" -ForegroundColor Cyan
    $stepStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed (exit code $LASTEXITCODE)."
    }
    Write-Host "    done in $($stepStopwatch.Elapsed.ToString('mm\:ss'))" -ForegroundColor DarkGray
}

# --- Preflight -------------------------------------------------------------
$pythonExe = Join-Path $root 'venv\Scripts\python.exe'
$pipExe = Join-Path $root 'venv\Scripts\pip.exe'
$pyinstaller = Join-Path $root 'venv\Scripts\pyinstaller.exe'
$lrelease = Join-Path $root 'venv\Scripts\pyside6-lrelease.exe'
$iscc = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$versionFile = Join-Path $root 'openlp\.version'
$pyprojectFile = Join-Path $root 'pyproject.toml'

foreach ($tool in @($pythonExe, $pipExe, $pyinstaller, $lrelease)) {
    if (-not (Test-Path $tool)) {
        throw "Not found: $tool. Activate/create the venv and 'pip install pyinstaller pyside6'."
    }
}
if (-not (Test-Path $versionFile)) {
    throw "Not found: $versionFile. The frozen app reads its version from this file."
}
$version = (Get-Content $versionFile -TotalCount 1).Trim()
Write-Host "Packaging OpenLP NCSDA/Noir version $version" -ForegroundColor Green

Invoke-Step 'Verifying venv Python and dependency versions' {
    $pyVersion = (& $pythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))").Trim()
    Write-Host "    Python:  $pyVersion (venv: $pythonExe)"
    # Supported/tested range; newer interpreters (e.g. a same-day release) can carry
    # untested CPython ABI/GC changes that surface as native crashes in compiled
    # extensions such as PySide6/Qt, so warn loudly rather than failing silently.
    $pyMajorMinor = [version]($pyVersion -replace '^(\d+\.\d+).*$', '$1')
    if ($pyMajorMinor -lt [version]'3.10' -or $pyMajorMinor -gt [version]'3.13') {
        Write-Warning "Python $pyVersion is outside the range this project is tested with (3.10-3.13). Builds and the frozen app may be unstable; consider rebuilding the venv with a supported Python version."
    }

    if (-not (Test-Path $pyprojectFile)) {
        Write-Warning "Not found: $pyprojectFile. Skipping PySide6 pin check."
    }
    else {
        $pinLine = Select-String -Path $pyprojectFile -Pattern '^\s*"PySide6\s*==\s*([0-9.]+)' | Select-Object -First 1
        if (-not $pinLine) {
            Write-Warning 'Could not find a pinned PySide6 version in pyproject.toml; skipping pin check.'
        }
        else {
            $pinnedVersion = $pinLine.Matches[0].Groups[1].Value
            $installedVersion = (& $pythonExe -c "import PySide6; print(PySide6.__version__)").Trim()
            Write-Host "    PySide6: $installedVersion (pinned: $pinnedVersion)"
            if ($installedVersion -ne $pinnedVersion) {
                throw "Installed PySide6 ($installedVersion) does not match the version pinned in pyproject.toml ($pinnedVersion). Run '$pipExe install `"PySide6==$pinnedVersion`"' before packaging, otherwise the frozen app will ship an untested Qt build."
            }
        }
    }
}

# --- 1. Translations -------------------------------------------------------
$i18nSrc = Join-Path $root 'resources\i18n'
$i18nOut = Join-Path $root 'build\i18n'
New-Item -ItemType Directory -Force $i18nOut | Out-Null
$tsFiles = Get-ChildItem (Join-Path $i18nSrc '*.ts')
Invoke-Step "Compiling $($tsFiles.Count) translation files" {
    $i = 0
    foreach ($ts in $tsFiles) {
        $i++
        $qm = Join-Path $i18nOut ($ts.BaseName + '.qm')
        Write-Host "    [$i/$($tsFiles.Count)] $($ts.Name)"
        & $lrelease $ts.FullName -qm $qm -silent
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "    failed to compile $($ts.Name) (exit code $LASTEXITCODE)"
            break
        }
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
    Write-Host "Total time: $($buildStopwatch.Elapsed.ToString('mm\:ss'))" -ForegroundColor Green
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
Write-Host "Total time: $($buildStopwatch.Elapsed.ToString('mm\:ss'))" -ForegroundColor Green
