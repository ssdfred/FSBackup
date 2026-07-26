$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Venv = Join-Path $Backend ".venv-build"
$Python = Join-Path $Venv "Scripts\python.exe"

Write-Host "Préparation de l’environnement de compilation FSBackup..."
if (-not (Test-Path $Python)) {
    py -3.13 -m venv $Venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Backend "requirements-runtime.txt") pyinstaller

Push-Location $Backend
try {
    Remove-Item -Recurse -Force "build", "dist" -ErrorAction SilentlyContinue
    & $Python -m PyInstaller --noconfirm "FSBackup.spec"
} finally {
    Pop-Location
}

$Executable = Join-Path $Backend "dist\FSBackup\FSBackup.exe"
if (-not (Test-Path $Executable)) {
    throw "La compilation n’a pas produit l’exécutable attendu : $Executable"
}

Write-Host "Compilation terminée : $Executable"
