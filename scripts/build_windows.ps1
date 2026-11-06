[CmdletBinding()]
param([switch]$KeepBuildFiles)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if ($env:OS -ne "Windows_NT") {
    throw "This script creates a Windows x64 executable and must run on Windows."
}
if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
    throw "The Windows Python Launcher was not found. Install 64-bit CPython 3.12."
}
$PythonCheck = & py -3.12 -c "import struct, sys; print(sys.version); print(struct.calcsize('P') * 8)"
if ($LASTEXITCODE -ne 0 -or $PythonCheck[-1] -ne "64") {
    throw "A 64-bit CPython 3.12 installation is required. Detected: $($PythonCheck -join ' / ')"
}

# Qt's deployment helper uses dumpbin from the Microsoft C++ toolchain to identify dependencies.
$ProgramFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$VsWhere = Join-Path $ProgramFilesX86 "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $VsWhere)) {
    throw "Visual Studio Build Tools 2022 with the C++ x64 toolchain is required (vswhere.exe not found)."
}
$VsInstall = & $VsWhere -latest -products "*" -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $VsInstall) {
    throw "Install Visual Studio Build Tools 2022 with the Desktop development with C++ workload."
}
$VcVars = Join-Path $VsInstall "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $VcVars)) {
    throw "The MSVC x64 environment script was not found: $VcVars"
}
$Command = '"' + $VcVars + '" >nul && set'
$DevEnvironment = & $env:ComSpec /d /s /c $Command
foreach ($Line in $DevEnvironment) {
    $Separator = $Line.IndexOf("=")
    if ($Separator -gt 0) {
        $Name = $Line.Substring(0, $Separator)
        $Value = $Line.Substring($Separator + 1)
        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}
if (-not (Get-Command dumpbin.exe -ErrorAction SilentlyContinue)) {
    throw "MSVC environment was loaded but dumpbin.exe is still unavailable."
}

$Venv = Join-Path $ProjectRoot ".venv-release"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$Deploy = Join-Path $Venv "Scripts\pyside6-deploy.exe"
if (-not (Test-Path $VenvPython)) {
    & py -3.12 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the release virtual environment." }
}

Write-Host "Installing pinned Windows x64 build dependencies…" -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements-build-win-x64.txt")
if ($LASTEXITCODE -ne 0) { throw "Pinned release dependency installation failed." }
& $VenvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw "pip check found a dependency conflict." }

Write-Host "Running static validation…" -ForegroundColor Cyan
& $VenvPython -m compileall -q main.py config.py core effects generators media rendering ui
if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }
& $VenvPython -m ruff check main.py config.py core effects generators media rendering ui
if ($LASTEXITCODE -ne 0) { throw "Ruff checks failed." }

$RequiredPaths = @(
    "resources\icons\Icon.ico",
    "resources\textures",
    "resources\sketches_and_strokes",
    "dictionary"
)
foreach ($RequiredPath in $RequiredPaths) {
    if (-not (Test-Path (Join-Path $ProjectRoot $RequiredPath))) {
        throw "Required bundled resource is missing: $RequiredPath"
    }
}
if (-not (Test-Path (Join-Path $ProjectRoot "THIRD_PARTY_NOTICES.md"))) {
    throw "THIRD_PARTY_NOTICES.md is missing; refusing to create an incomplete release."
}
if (-not (Test-Path $Deploy)) {
    throw "pyside6-deploy was not installed into the release environment."
}

# Recreate the deployment spec so pyproject.toml is the authoritative configuration.
$SpecPath = Join-Path $ProjectRoot "pysidedeploy.spec"
if (Test-Path $SpecPath) { Remove-Item $SpecPath -Force }
if (-not $KeepBuildFiles) {
    foreach ($Path in @("build", "dist")) {
        $FullPath = Join-Path $ProjectRoot $Path
        if (Test-Path $FullPath) { Remove-Item $FullPath -Recurse -Force }
    }
}

Write-Host "Generating PySide6 deployment configuration…" -ForegroundColor Cyan
& $Deploy "main.py" --init
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $SpecPath)) {
    throw "pyside6-deploy could not generate pysidedeploy.spec."
}

# PySide6 6.12's default spec pins an older Nuitka. Override it so the version
# used by the compiler matches the version installed from our build profile.
$SpecContent = Get-Content $SpecPath -Raw
if ($SpecContent -notmatch "(?m)^\[python\]\s*$") {
    throw "Unexpected pysidedeploy.spec format: [python] section not found."
}
if ($SpecContent -notmatch "(?m)^packages\s*=") {
    throw "Unexpected pysidedeploy.spec format: [python] packages entry not found."
}
$SpecContent = [regex]::Replace(
    $SpecContent,
    "(?m)^packages\s*=.*$",
    "packages = Nuitka==4.3.4,ordered-set,zstandard"
)
Set-Content -Path $SpecPath -Value $SpecContent -Encoding utf8

Write-Host "Building the one-file Windows executable…" -ForegroundColor Cyan
& $Deploy -c $SpecPath --mode onefile --no-install --force
if ($LASTEXITCODE -ne 0) {
    throw "pyside6-deploy failed. Run this script in a Windows x64 MSVC environment."
}

$Executables = @(Get-ChildItem (Join-Path $ProjectRoot "dist") -Filter "*.exe" -File)
if ($Executables.Count -ne 1) {
    throw "Expected one executable in dist; found $($Executables.Count). Inspect the deployment output."
}
$Executable = $Executables[0]

Write-Host "Checking the packaged runtime and bundled resources…" -ForegroundColor Cyan
$SelfCheckOutput = & $Executable.FullName --self-check 2>&1
$SelfCheckExitCode = $LASTEXITCODE
$SelfCheckOutput | ForEach-Object { Write-Host $_ }
if ($SelfCheckExitCode -ne 0) {
    throw "The packaged executable self-check failed with exit code $SelfCheckExitCode."
}

$Hash = Get-FileHash $Executable.FullName -Algorithm SHA256
$SizeMiB = [math]::Round($Executable.Length / 1MB, 1)
Write-Host ""
Write-Host "BUILD COMPLETE" -ForegroundColor Green
Write-Host "Executable: $($Executable.FullName)"
Write-Host "Size:       $SizeMiB MiB"
Write-Host "SHA-256:    $($Hash.Hash)"
Write-Host "Copy this one .exe to the target Windows x64 computer."
Write-Host "A GPU driver with OpenGL 3.3 and Sonic Pi remain external requirements."
