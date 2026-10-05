# Cria o ambiente virtual .venv e instala o projeto

param([switch]$Dev)
$ErrorActionPreference= "Stop"
Set-Location $PSScriptRoot

$py = if ($env:PYTHON) { $env:PYTHON } else { "py" }
& $py -c "import sys; assert sys.version_info >= (3, 10), 'Python >= 3.10 necessário'"

if (-not (Test-Path .venv)) { & $py -m venv .venv }
$vpy = ".\.venv\Scripts\python.exe"

& $vpy -m pip install --upgrade pip -q
& $vpy -m pip install -r requirements.lock -q
if ($Dev) { & $vpy -m pip install -e ".[dev]" -q } else { & $vpy -m pip install -e . --no-deps -q }

Write-Host "Ok Ambiente pronto em .venv"
Write-Host " Ative com: .\venv\Scripts\Activate.ps1"
Write-Host " Depois: radar --help"