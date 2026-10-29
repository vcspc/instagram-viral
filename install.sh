#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================================="
echo "  Instagram Viral Reels AI Agent - Instalador Unix"
echo "==================================================="
echo ""

# Identifica o comando python3
if command -v python3 &>/dev/null; then
    PY_BIN="python3"
elif command -v python &>/dev/null; then
    PY_BIN="python"
else
    echo "[ERRO] Python 3 não foi encontrado no sistema."
    echo "Instale o Python 3.10 ou superior antes de prosseguir."
    exit 1
fi

# Auxílio de instalação automática de pacotes do sistema se o usuário estiver em Linux/macOS
if ! command -v ffmpeg &>/dev/null; then
    echo "[AVISO] FFmpeg não encontrado. Tentando instalar utilitários do sistema..."
    if command -v apt-get &>/dev/null; then
        echo "Executando: sudo apt update && sudo apt install -y ffmpeg python3-venv libsndfile1"
        sudo apt-get update && sudo apt-get install -y ffmpeg python3-venv libsndfile1 || true
    elif command -v brew &>/dev/null; then
        echo "Executando: brew install ffmpeg"
        brew install ffmpeg || true
    elif command -v dnf &>/dev/null; then
        echo "Executando: sudo dnf install -y ffmpeg"
        sudo dnf install -y ffmpeg || true
    elif command -v pacman &>/dev/null; then
        echo "Executando: sudo pacman -S --noconfirm ffmpeg"
        sudo pacman -S --noconfirm ffmpeg || true
    fi
fi

# Executa o instalador principal em Python
$PY_BIN install.py "$@"
