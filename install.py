#!/usr/bin/env python3
"""Instalador e Atualizador Multiplataforma para o Instagram Viral Reels AI Agent.

Funciona de forma nativa em Windows, Linux e macOS utilizando apenas
módulos da biblioteca padrão do Python.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / ".venv"

# Cores ANSI e suporte a UTF-8 no Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        os.system("")
    except Exception:
        pass

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Símbolos com fallback para terminais legados
OK_SYM = "[OK]" if sys.platform == "win32" and getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8") else "✓"
ERR_SYM = "[X]" if sys.platform == "win32" and getattr(sys.stdout, "encoding", "").lower() not in ("utf-8", "utf8") else "✗"


def print_banner():
    banner = f"""
{CYAN}{BOLD}======================================================================
     Instagram Viral Reels AI Agent - Instalador Multiplataforma
======================================================================{RESET}
Sistema Operacional Detectado: {BOLD}{platform.system()} {platform.release()} ({platform.machine()}){RESET}
Versão do Python: {BOLD}{sys.version.split()[0]}{RESET}
Diretório Base: {BASE_DIR}
----------------------------------------------------------------------
"""
    print(banner)


def log_step(step_num: int, title: str):
    print(f"\n{CYAN}{BOLD}[{step_num}] {title}{RESET}")


def log_success(msg: str):
    print(f"  {GREEN}{OK_SYM} {msg}{RESET}")


def log_warning(msg: str):
    print(f"  {YELLOW}! {msg}{RESET}")


def log_error(msg: str):
    print(f"  {RED}{ERR_SYM} {msg}{RESET}")


def get_venv_python() -> Path:
    """Retorna o caminho do executável Python dentro do ambiente virtual."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def get_venv_pip() -> Path:
    """Retorna o caminho do executável pip dentro do ambiente virtual."""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def check_python_version() -> bool:
    """Garante que a versão do Python é 3.10 ou superior."""
    log_step(1, "Verificando compatibilidade do Python...")
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        log_error(f"Python 3.10 ou superior é necessário. Versão atual: {major}.{minor}")
        return False
    log_success(f"Python {major}.{minor} é totalmente compatível.")
    return True


def check_ffmpeg() -> bool:
    """Verifica a presença do FFmpeg no sistema ou orienta a instalação."""
    log_step(2, "Verificando instalação do FFmpeg...")
    ffmpeg_path = shutil.which("ffmpeg")

    # Verifica também caminho npm comum no Windows
    if not ffmpeg_path and sys.platform == "win32":
        appdata_npm = Path(os.environ.get("APPDATA", "")) / "npm" / "ffmpeg.exe"
        if appdata_npm.exists():
            ffmpeg_path = str(appdata_npm)

    if ffmpeg_path:
        log_success(f"FFmpeg encontrado em: {ffmpeg_path}")
        return True

    log_warning("FFmpeg não foi localizado no PATH do sistema.")
    system = platform.system().lower()
    print("  Para instalar o FFmpeg automaticamente no seu sistema operacional:")
    if system == "windows":
        print(f"    {YELLOW}winget install Gyan.FFmpeg{RESET}  ou  {YELLOW}choco install ffmpeg{RESET}")
    elif system == "darwin":  # macOS
        print(f"    {YELLOW}brew install ffmpeg{RESET}")
    elif "linux" in system:
        print(f"    Ubuntu/Debian: {YELLOW}sudo apt update && sudo apt install -y ffmpeg{RESET}")
        print(f"    Fedora:        {YELLOW}sudo dnf install -y ffmpeg{RESET}")
        print(f"    Arch Linux:    {YELLOW}sudo pacman -S ffmpeg{RESET}")
    print("  (A aplicação poderá funcionar para pesquisa, mas a conversão de áudio para Whisper requer o FFmpeg).\n")
    return False


def setup_virtualenv() -> bool:
    """Cria ou valida o ambiente virtual .venv."""
    log_step(3, "Configurando Ambiente Virtual (.venv)...")
    venv_py = get_venv_python()

    if not venv_py.exists():
        print(f"  Criando ambiente virtual isolado em {VENV_DIR}...")
        try:
            import venv
            builder = venv.EnvBuilder(with_pip=True)
            builder.create(VENV_DIR)
            log_success("Ambiente virtual criado com sucesso.")
        except Exception as exc:
            log_error(f"Falha ao criar ambiente virtual com módulo nativo: {exc}")
            # Fallback chamando sys.executable
            try:
                subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
                log_success("Ambiente virtual criado via subprocesso.")
            except Exception as e2:
                log_error(f"Não foi possível criar o venv: {e2}")
                return False
    else:
        log_success(f"Ambiente virtual existente validado em: {VENV_DIR}")

    return True


def install_dependencies(upgrade: bool = False) -> bool:
    """Instala ou atualiza as dependências via pip no .venv."""
    action = "Atualizando" if upgrade else "Instalando"
    log_step(4, f"{action} dependências Python a partir de requirements.txt...")

    req_file = BASE_DIR / "requirements.txt"
    if not req_file.exists():
        log_error("Arquivo requirements.txt não encontrado.")
        return False

    venv_pip = get_venv_pip()
    pip_cmd = [str(venv_pip), "install"]
    if upgrade:
        pip_cmd.append("--upgrade")
    pip_cmd.extend(["-r", str(req_file)])

    print(f"  Executando: {' '.join(pip_cmd)}")
    try:
        # Atualiza o pip primeiro silenciosamente
        subprocess.run([str(venv_pip), "install", "--upgrade", "pip"], capture_output=True)
        # Instala requirements
        res = subprocess.run(pip_cmd)
        if res.returncode != 0:
            log_error("Falha ao instalar dependências.")
            return False
        log_success("Todas as dependências foram instaladas e verificadas com sucesso.")
        return True
    except Exception as exc:
        log_error(f"Erro durante a execução do pip: {exc}")
        return False


def setup_env_file() -> bool:
    """Verifica e inicializa o arquivo .env a partir do .env.example."""
    log_step(5, "Verificando arquivo de configurações (.env)...")
    env_file = BASE_DIR / ".env"
    env_example = BASE_DIR / ".env.example"

    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            log_success("Arquivo .env criado a partir do modelo .env.example.")
            print(f"  {YELLOW}-> Abra o arquivo .env e preencha sua GEMINI_API_KEY e credenciais do Instagram.{RESET}")
        else:
            log_warning("Arquivo .env.example não encontrado para cópia inicial.")
    else:
        log_success("Arquivo .env já existente detectado.")

    # Cria pastas essenciais
    (BASE_DIR / "sessions").mkdir(exist_ok=True)
    (BASE_DIR / "outputs").mkdir(exist_ok=True)
    return True


def run_unit_tests() -> bool:
    """Executa a suíte de testes unitários dentro do venv."""
    log_step(6, "Executando testes automatizados para validação do sistema...")
    venv_py = get_venv_python()
    cmd = [str(venv_py), "-m", "unittest", "discover", "-s", "tests", "-v"]

    try:
        res = subprocess.run(cmd)
        if res.returncode == 0:
            log_success("Todos os testes unitários passaram com sucesso!")
            return True
        else:
            log_warning("Alguns testes falharam. Verifique os relatórios acima.")
            return False
    except Exception as exc:
        log_warning(f"Não foi possível rodar os testes: {exc}")
        return False


def update_from_git() -> bool:
    """Verifica e baixa as últimas atualizações do repositório Git, se presente."""
    log_step(0, "Verificando atualizações no Git...")
    git_dir = BASE_DIR / ".git"
    if not git_dir.exists():
        log_warning("Diretório .git não encontrado. Pulando etapa de git pull.")
        return False

    git_bin = shutil.which("git")
    if not git_bin:
        log_warning("Git não encontrado no PATH.")
        return False

    try:
        print("  Puxando alterações mais recentes (git pull)...")
        subprocess.run([git_bin, "pull"], cwd=BASE_DIR, check=True)
        log_success("Repositório atualizado com sucesso!")
        return True
    except Exception as exc:
        log_warning(f"Aviso no git pull: {exc}")
        return False


def create_launchers():
    """Gera scripts convenientes de inicialização rápida conforme o SO."""
    # Script para Windows (.bat)
    run_bat = BASE_DIR / "run.bat"
    bat_content = """@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\\Scripts\\python.exe" (
    set "PY_EXEC=.venv\\Scripts\\python.exe"
) else (
    set "PY_EXEC=python"
)

if "%~1"=="" (
    echo Iniciando Painel Web Dashboard...
    "%PY_EXEC%" -m src.main ui
) else (
    "%PY_EXEC%" -m src.main %*
)
endlocal
"""
    run_bat.write_text(bat_content, encoding="utf-8")

    # Script para Linux / macOS (.sh)
    run_sh = BASE_DIR / "run.sh"
    sh_content = """#!/usr/bin/env bash
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
"""
    run_sh.write_text(sh_content, encoding="utf-8")
    try:
        run_sh.chmod(0o755)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Instalador e Atualizador do Instagram Viral Reels AI Agent"
    )
    parser.add_argument(
        "--update", "-u", action="store_true", help="Atualiza a aplicação (git pull) e dependências."
    )
    parser.add_argument(
        "--check", "-c", action="store_true", help="Apenas verifica dependências e ambiente."
    )
    parser.add_argument(
        "--no-tests", action="store_true", help="Pula a execução da suíte de testes."
    )
    args = parser.parse_args()

    print_banner()

    if args.update:
        print(f"{YELLOW}{BOLD}>>> INICIANDO ATUALIZAÇÃO DA APLICAÇÃO <<<{RESET}")
        update_from_git()

    if not check_python_version():
        sys.exit(1)

    check_ffmpeg()

    if args.check:
        print(f"\n{GREEN}{BOLD}Diagnóstico concluído com sucesso!{RESET}\n")
        sys.exit(0)

    if not setup_virtualenv():
        sys.exit(1)

    if not install_dependencies(upgrade=args.update):
        sys.exit(1)

    setup_env_file()
    create_launchers()

    if not args.no_tests:
        run_unit_tests()

    print(f"""
{GREEN}{BOLD}======================================================================
     INSTALAÇÃO / ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!
======================================================================{RESET}

Como iniciar a aplicação:

1. {BOLD}Interface Visual Web (Dashboard):{RESET}
   - No Windows:      {CYAN}run.bat ui{RESET}  (ou dê um duplo clique em run.bat)
   - No Linux/macOS:  {CYAN}./run.sh ui{RESET}

2. {BOLD}Pesquisa por Nicho (Terminal):{RESET}
   - No Windows:      {CYAN}run.bat search -q "bolos decorados simples" -t 1m{RESET}
   - No Linux/macOS:  {CYAN}./run.sh search -q "bolos decorados simples" -t 1m{RESET}

3. {BOLD}Auditoria de Perfil (Terminal):{RESET}
   - No Windows:      {CYAN}run.bat profile lucureau -n 3{RESET}
   - No Linux/macOS:  {CYAN}./run.sh profile lucureau -n 3{RESET}

4. {BOLD}Para Atualizar no Futuro:{RESET}
   - {CYAN}python install.py --update{RESET}
""")


if __name__ == "__main__":
    main()
