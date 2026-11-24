# Construye los ejecutables de Windows con PyInstaller.
#
#   .\build.ps1              # emisor y receptor
#   .\build.ps1 emisor       # solo uno
#   .\build.ps1 -Clean       # borra build/ y dist/ antes de compilar
#
# Requiere: pip install -r requirements-dev.txt

param(
    [ValidateSet("emisor", "receptor", "todos")]
    [string]$Target = "todos",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "PyInstaller no está instalado. Ejecuta: pip install -r requirements-dev.txt"
}

if ($Clean) {
    foreach ($dir in @("build", "dist")) {
        if (Test-Path $dir) { Remove-Item $dir -Recurse -Force }
    }
    Write-Host "Carpetas build/ y dist/ eliminadas." -ForegroundColor DarkGray
}

$specs = switch ($Target) {
    "emisor"   { @("emisor.spec") }
    "receptor" { @("receptor.spec") }
    default    { @("emisor.spec", "receptor.spec") }
}

foreach ($spec in $specs) {
    Write-Host "Compilando $spec ..." -ForegroundColor Cyan
    pyinstaller --noconfirm --clean $spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló con $spec (código $LASTEXITCODE)" }
}

Write-Host ""
Write-Host "Listo. Ejecutables en dist\:" -ForegroundColor Green
Get-ChildItem dist -Filter *.exe | ForEach-Object { "  dist\$($_.Name)" }
