"""Gerenciador do ciclo de vida de download, conversão e transcrição de áudio."""
import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from instagrapi import Client
from src.audio.converter import AudioConverter
from src.audio.downloader import ReelDownloader
from src.audio.transcriber import WhisperTranscriber
from src.models.instagram import ReelItem

logger = logging.getLogger(__name__)


class AudioTranscriptionManager:
    """Orquestra o download dos vídeos, conversão para WAV e transcrição via Whisper."""

    def __init__(
        self,
        client: Client | None = None,
        whisper_model: str = "base",
        device: str = "cpu",
        ffmpeg_path: str | None = None,
    ):
        self.downloader = ReelDownloader(client=client)
        self.converter = AudioConverter(ffmpeg_path=ffmpeg_path)
        self.transcriber = WhisperTranscriber(model_size=whisper_model, device=device)

    def process_top_reels(
        self,
        reels: list[ReelItem],
        top_n: int = 3,
        status_callback: Callable[[str], None] | None = None,
    ) -> list[ReelItem]:
        """Baixa e transcreve os Top N Reels mais virais da lista informada."""
        if not reels or top_n <= 0:
            return reels

        target_reels = reels[:top_n]
        temp_dir = Path(tempfile.mkdtemp(prefix="ig_audio_"))
        logger.info(f"Diretório temporário criado para áudio: {temp_dir}")

        try:
            for idx, reel in enumerate(target_reels, 1):
                msg = f"Processando áudio do Reel #{idx} ({reel.code} - Score: {reel.metrics.viral_score:.1f})..."
                logger.info(msg)
                if status_callback:
                    status_callback(msg)

                try:
                    # 1. Download do vídeo MP4
                    video_path = self.downloader.download_video(reel, target_dir=temp_dir)

                    # 2. Conversão para WAV 16kHz via FFmpeg
                    wav_path = self.converter.video_to_whisper_audio(video_path)

                    # 3. Transcrição com timestamps via Whisper
                    transcript = self.transcriber.transcribe(wav_path)
                    reel.transcript = transcript

                    logger.info(
                        f"Reel {reel.code} transcrito com sucesso! "
                        f"Gancho 3s: '{transcript.hook_text_3s[:60]}...'"
                    )
                except Exception as exc:
                    logger.warning(f"Não foi possível transcrever o Reel {reel.code}: {exc}")

        finally:
            # Limpeza estrita e imediata de todos os arquivos de vídeo e áudio baixados
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Arquivos temporários de vídeo e áudio removidos com sucesso.")
            except Exception as exc:
                logger.debug(f"Aviso ao remover diretório temporário: {exc}")

        return reels
