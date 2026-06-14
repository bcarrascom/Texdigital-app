# build_windows.ps1 — Empaqueta la app en un .exe de Windows con PyInstaller.
# Ejecutar desde la carpeta empresa_app:  powershell -ExecutionPolicy Bypass -File build_windows.ps1

$ErrorActionPreference = "Stop"

$AppName  = "Sistema de Gestion"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Verificando Python ==="
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python no esta instalado."
    Write-Host "Descargalo desde https://www.python.org/downloads/"
    exit 1
}
python --version

Write-Host ""
Write-Host "=== Instalando dependencias ==="
python -m pip install --upgrade pip --quiet
python -m pip install pyinstaller -r "$ScriptDir\requirements.txt" --quiet

Write-Host ""
Write-Host "=== Limpiando builds anteriores ==="
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$ScriptDir\build", "$ScriptDir\dist", "$ScriptDir\$AppName.spec"

Write-Host ""
Write-Host "=== Empaquetando... ==="
Set-Location $ScriptDir

python -m PyInstaller `
    --name "$AppName" `
    --windowed `
    --onedir `
    --collect-all openpyxl `
    --add-data "recursos;recursos" `
    --hidden-import "PIL._tkinter_finder" `
    main.py

if (-not $env:CI) {
    Write-Host ""
    Write-Host "=== Creando acceso directo en el Escritorio ==="
    $desktop = [Environment]::GetFolderPath("Desktop")
    $exePath = "$ScriptDir\dist\$AppName\$AppName.exe"
    $shortcutPath = "$desktop\$AppName.lnk"

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $exePath
    $shortcut.WorkingDirectory = "$ScriptDir\dist\$AppName"
    $shortcut.Save()

    Write-Host "Acceso directo creado en el Escritorio: $AppName.lnk"
}

Write-Host ""
Write-Host "=== Listo ==="
Write-Host "El archivo esta en:  dist\$AppName\$AppName.exe"
