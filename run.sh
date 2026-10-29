#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
    PY_EXEC=".venv/bin/python"
else
    PY_EXEC="python3"
fi

if [ -z "$1" ]; then
    echo "Iniciando Painel Web Dashboard..."
    "$PY_EXEC" -m src.main ui
else
    "$PY_EXEC" -m src.main "$@"
fi
