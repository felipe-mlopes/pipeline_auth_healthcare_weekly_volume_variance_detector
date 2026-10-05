# !/usr/bin/env bash

# Cria o ambiente virtual .venv e instala o projeto

set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info >= (3, 10), "Python >= 3.10 necessário"'

[ -d .venv ] || "$PY" -m venv .venv
if [ -f .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe; else VPY=.venv/bin/python; fi

"$VPY" -m pip install --upgrade pip -q
"$VPY" -m pip install -r requirements.lock -q
if [ "${1:-}" = "--dev" ]; then
    "$VPY" -m pip install -e ".[dev]" -q
else
    "$VPY" -m pip install -e . --no-deps -q
fi
[ -f .env ] || cp .env.example .env

echo " Ambiente protno em .venv"
echo " Ative com: source .venv/bin/activate (Windows Git Bash: source .venv/Scripts/activate)"
echo " Depois: radar --help"