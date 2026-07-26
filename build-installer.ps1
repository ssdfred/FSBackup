param(
    [switch]$SkipApplicationBuild
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallerScript = Join-Path $Root "installer\FSBackup.iss"
$ReleaseDirectory = Join-Path $Root "release"
$ApplicationExecutable = Join-Path $Root "backend\dist\FSBackup\FSBackup.exe"

if (-not $SkipApplicationBuild) {
    & (Join-Path $Root "build-windows.ps1")
}

if (-not (Test-Path $ApplicationExecutable)) {
    throw "L’exécutable FSBackup est introuvable : $ApplicationExecutable"
}

$Candidates = @(
    $env:INNO_SETUP_COMPILER,
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
) | Where-Object { $_ }

$Compiler = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Compiler) {
    throw @"
Inno Setup 6 est requis pour générer l’installateur.
Installez-le puis relancez ce script :
  winget install --id JRSoftware.InnoSetup -e
Vous pouvez aussi définir INNO_SETUP_COMPILER avec le chemin complet de ISCC.exe.
"@
}

Remove-Item -Recurse -Force $ReleaseDirectory -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $ReleaseDirectory -Force | Out-Null

Write-Host "Compilation de l’installateur FSBackup avec $Compiler..."
& $Compiler $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw "La compilation Inno Setup a échoué avec le code $LASTEXITCODE."
}

$Installer = Get-ChildItem $ReleaseDirectory -Filter "FSBackup-Setup-*.exe" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $Installer) {
    throw "Aucun installateur n’a été produit dans $ReleaseDirectory."
}

$Hash = Get-FileHash -Algorithm SHA256 $Installer.FullName
$HashFile = "$($Installer.FullName).sha256"
"$($Hash.Hash.ToLowerInvariant())  $($Installer.Name)" | Set-Content -Encoding ascii $HashFile

Write-Host "Installateur terminé : $($Installer.FullName)"
Write-Host "Empreinte SHA-256 : $HashFile"
