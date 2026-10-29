"""Conversão de vídeo MP4 para áudio WAV otimizado para Whisper via FFmpeg."""
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioConverter:
    """Extrai e converte a faixa de áudio de arquivos de vídeo utilizando FFmpeg."""

    def __init__(self, ffmpeg_path: str | None = None):
        self.ffmpeg_bin = self._resolve_ffmpeg(ffmpeg_path)

    def _resolve_ffmpeg(self, custom_path: str | None) -> str:
        """Localiza o binário do FFmpeg no sistema ou em caminhos conhecidos."""
        if custom_path and Path(custom_path).exists():
            return custom_path

        found = shutil.which("ffmpeg")
        if found:
            return found

        # Caminho conhecido no ambiente Windows do usuário
        appdata_npm = Path(os.environ.get("APPDATA", "")) / "npm" / "ffmpeg.exe"
        if appdata_npm.exists():
            return str(appdata_npm)

        raise FileNotFoundError(
            "O executável 'ffmpeg' não foi encontrado no PATH do sistema. "
            "Certifique-se de que o FFmpeg está instalado e disponível."
        )

    def video_to_whisper_audio(self, video_path: Path, output_path: Path | None = None) -> Path:
        """Converte um arquivo de vídeo MP4 em áudio WAV (16kHz, mono, PCM 16-bit)."""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Arquivo de vídeo não encontrado: {video_path}")

        if output_path is None:
            output_path = video_path.with_suffix(".wav")
        else:
            output_path = Path(output_path)

        cmd = [
            self.ffmpeg_bin,
            "-y",  # Sobrescreve sem perguntar
            "-i", str(video_path),
            "-vn",  # Desativa faixa de vídeo
            "-acodec", "pcm_s16le",  # PCM 16-bit
            "-ar", "16000",  # Taxa de amostragem ideal do Whisper: 16.000 Hz
            "-ac", "1",  # 1 canal (mono)
            str(output_path),
        ]

        logger.debug(f"Executando comando FFmpeg: {' '.join(cmd)}")

        creation_flags = 0
        if sys.platform == "win32":
            # Evita que uma janela preta de console apareça no Windows
            creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creation_flags,
            text=True,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            # Trata caso de vídeo sem faixa de áudio (mudo)
            if "does not contain any stream" in error_msg or "Output file is empty" in error_msg:
                logger.warning(f"O vídeo {video_path.name} parece não possuir faixa de áudio audível.")
            raise RuntimeError(f"Falha na conversão com FFmpeg: {error_msg[-300:]}")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"O FFmpeg gerou um arquivo de áudio vazio para {video_path.name}")

        logger.info(f"Áudio WAV gerado com sucesso: {output_path.name} ({output_path.stat().st_size} bytes)")
        return output_path
