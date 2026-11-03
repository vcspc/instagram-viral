#!/usr/bin/env python3
"""Script de automação para empacotar a aplicação em um executável (.exe) standalone.

Utiliza PyInstaller e empacota todos os arquivos estáticos (HTML/Tailwind),
modelos Pydantic, bibliotecas de áudio e o executável do FFmpeg.
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Suporte seguro a UTF-8 no console do Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"


def check_and_install_pyinstaller():
    """Garante que o PyInstaller está disponível."""
    try:
        import PyInstaller
        print(f"[✓] PyInstaller {PyInstaller.__version__} detectado.")
    except ImportError:
        print("[!] PyInstaller não encontrado. Instalando automaticamente...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("[✓] PyInstaller instalado com sucesso.")


def find_ffmpeg() -> Path | None:
    """Localiza o binário do FFmpeg no sistema para embutir no pacote."""
    found = shutil.which("ffmpeg")
    if found:
        return Path(found)

    if sys.platform == "win32":
        appdata_npm = Path(os.environ.get("APPDATA", "")) / "npm" / "ffmpeg.exe"
        if appdata_npm.exists():
            return appdata_npm

    return None


def build_executable():
    """Executa o build via PyInstaller."""
    print("\n" + "=" * 70)
    print("   Empacotamento do Instagram Viral Reels AI Agent")
    print(f"   Sistema: {platform.system()} {platform.machine()}")
    print("=" * 70 + "\n")

    check_and_install_pyinstaller()

    main_script = BASE_DIR / "src" / "main.py"
    if not main_script.exists():
        print(f"[ERRO] Arquivo principal não encontrado: {main_script}")
        sys.exit(1)

    app_name = "InstagramViral"
    sep = ";" if sys.platform == "win32" else ":"

    # Encerra instâncias anteriores do executável para evitar bloqueio de arquivos
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/IM", f"{app_name}.exe"], capture_output=True)
        except Exception:
            pass

    # Dados adicionais necessários (front-end estático e .env.example)
    static_src = BASE_DIR / "src" / "web" / "static"
    static_dst = Path("src") / "web" / "static"

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name", app_name,
        "--noconfirm",
        "--clean",
        # Modo diretório (melhor para IA/Whisper devido ao tamanho de DLLs e carregamento instantâneo)
        "--onedir",
        "--add-data", f"{static_src}{sep}{static_dst}",
        "--add-data", f"{BASE_DIR / '.env.example'}{sep}.",
        # Coleta completa de bibliotecas de IA e áudio (incluindo modelos ONNX, VAD e DLLs)
        "--collect-all", "faster_whisper",
        "--collect-all", "ctranslate2",
        "--collect-all", "onnxruntime",
        "--collect-all", "soundfile",
        # Hidden imports essenciais
        "--hidden-import", "aiohttp",
        "--hidden-import", "aiohttp.web",
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic_settings",
        "--hidden-import", "rich",
        "--hidden-import", "typer",
        "--hidden-import", "pyotp",
        str(main_script),
    ]

    print("[*] Iniciando compilação com PyInstaller...")
    print(f"    Comando: {' '.join(cmd)}\n")
    subprocess.run(cmd, check=True)

    output_app_dir = DIST_DIR / app_name

    # 1. Copia o FFmpeg para dentro do pacote final (se encontrado)
    ffmpeg_bin = find_ffmpeg()
    if ffmpeg_bin and ffmpeg_bin.exists():
        target_ffmpeg = output_app_dir / ffmpeg_bin.name
        print(f"[*] Embutindo FFmpeg ({ffmpeg_bin.name}) no pacote final...")
        shutil.copy2(ffmpeg_bin, target_ffmpeg)
        print(f"[✓] FFmpeg copiado para: {target_ffmpeg}")

    # 2. Configura arquivo .env no pacote
    target_env = output_app_dir / ".env"
    local_env = BASE_DIR / ".env"
    env_example = BASE_DIR / ".env.example"

    if local_env.exists():
        print("[*] Copiando arquivo de configurações .env para o pacote...")
        shutil.copy2(local_env, target_env)
    elif env_example.exists():
        shutil.copy2(env_example, target_env)

    # 3. Preserva sessões autenticadas existentes
    target_sessions = output_app_dir / "sessions"
    target_sessions.mkdir(parents=True, exist_ok=True)
    local_sessions = BASE_DIR / "sessions"
    if local_sessions.exists():
        for s_file in local_sessions.glob("*.session.json"):
            shutil.copy2(s_file, target_sessions / s_file.name)
            print(f"[✓] Sessão ativa copiada para o pacote: {s_file.name}")

    # 4. Garante diretório outputs no pacote
    (output_app_dir / "outputs").mkdir(parents=True, exist_ok=True)

    # 5. Cria atalho 'Iniciar-Dashboard.bat' para usuários no Windows
    if sys.platform == "win32":
        launcher_bat = output_app_dir / "Iniciar-Dashboard.bat"
        launcher_bat.write_text(
            "@echo off\n"
            "cd /d \"%~dp0\"\n"
            "echo Iniciando Instagram Viral Reels AI...\n"
            f"start \"\" \"{app_name}.exe\"\n",
            encoding="utf-8",
        )
        print(f"[✓] Atalho de inicialização criado: {launcher_bat.name}")

    print("\n" + "=" * 70)
    print("   BUILD CONCLUÍDO COM SUCESSO!")
    print(f"   Pasta gerada: {output_app_dir}")
    print(f"   Executável:   {output_app_dir / (app_name + ('.exe' if sys.platform == 'win32' else ''))}")
    print("=" * 70 + "\n")
    print("Para distribuir para usuários finais:")
    print(f"1. Compacte a pasta '{output_app_dir}' em um arquivo ZIP.")
    print(f"2. O usuário só precisa descompactar e dar um DUPLO CLIQUE no executável '{app_name}.exe'!")
    print("3. O navegador abrirá automaticamente com o Dashboard visual pronto para uso.")
    print("4. O usuário poderá preencher a chave do Gemini e a conta do Instagram direto na página web!")


if __name__ == "__main__":
    build_executable()
