"""Ponto de entrada executável da aplicação."""
import sys

# Assegura suporte a UTF-8 no console do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.cli.app import app

if __name__ == "__main__":
    # Se executado sem argumentos (ex: duplo clique direto no .exe), abre a UI automaticamente
    if len(sys.argv) <= 1:
        sys.argv.append("ui")
    app()
