"""Gerenciador do ciclo de vida de download, transcrição de áudio e análise visual de ganchos."""
import logging
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from instagrapi import Client
from src.agent.gemini_client import GeminiClient
from src.audio.converter import AudioConverter
from src.audio.downloader import ReelDownloader
from src.audio.transcriber import WhisperTranscriber
from src.models.instagram import ReelItem
from src.vision.frame_extractor import FrameExtractor
from src.vision.visual_analyzer import VisualHookAnalyzer

logger = logging.getLogger(__name__)


class AudioTranscriptionManager:
    """Orquestra download dos vídeos, conversão para WAV, transcrição via Whisper e visão computacional via Gemini."""

    def __init__(
        self,
        client: Client | None = None,
        whisper_model: str = "base",
        device: str = "cpu",
        ffmpeg_path: str | None = None,
        language: str | None = "pt",
        gemini_client: GeminiClient | None = None,
        enable_vision: bool = True,
    ):
        self.downloader = ReelDownloader(client=client)
        self.converter = AudioConverter(ffmpeg_path=ffmpeg_path)
        self.transcriber = WhisperTranscriber(model_size=whisper_model, device=device)
        self.language = language
        self.gemini_client = gemini_client
        self.enable_vision = enable_vision
        self.frame_extractor = FrameExtractor(ffmpeg_path=ffmpeg_path)
        self.visual_analyzer = VisualHookAnalyzer(gemini_client=gemini_client) if gemini_client else None

    def process_top_reels(
        self,
        reels: list[ReelItem],
        top_n: int = 3,
        status_callback: Callable[[str], None] | None = None,
    ) -> list[ReelItem]:
        """Baixa, transcreve com Whisper e analisa os 3s do gancho visual dos Top N Reels."""
        if not reels or top_n <= 0:
            return reels

        target_reels = reels[:top_n]
        temp_dir = Path(tempfile.mkdtemp(prefix="ig_media_"))
        logger.info(f"Diretório temporário criado para mídia: {temp_dir}")

        try:
            for idx, reel in enumerate(target_reels, 1):
                msg = f"Processando Reel #{idx} ({reel.code} - Score: {reel.metrics.viral_score:.1f})..."
                logger.info(msg)
                if status_callback:
                    status_callback(msg)

                try:
                    # 1. Download do vídeo MP4
                    video_path = self.downloader.download_video(reel, target_dir=temp_dir)

                    # 2. Conversão para WAV 16kHz via FFmpeg
                    wav_path = self.converter.video_to_whisper_audio(video_path)

                    # 3. Transcrição com timestamps via Whisper no idioma configurado
                    transcript = self.transcriber.transcribe(wav_path, language=self.language)
                    reel.transcript = transcript

                    logger.info(
                        f"Reel {reel.code} transcrito com sucesso! "
                        f"Gancho 3s falado: '{transcript.hook_text_3s[:60]}...'"
                    )

                    # 4. Extração e Análise Visual dos 3 primeiros segundos via Gemini Vision
                    if self.enable_vision and self.visual_analyzer:
                        msg_vis = f"Analisando gancho visual (3 frames dos primeiros 3s) do Reel #{idx} via Gemini Vision..."
                        logger.info(msg_vis)
                        if status_callback:
                            status_callback(msg_vis)

                        try:
                            # Extrai 3 frames nos primeiros 3 segundos
                            frame_paths = self.frame_extractor.extract_hook_frames(
                                video_path=video_path,
                                output_dir=temp_dir,
                                timestamps=[0.8, 1.8, 2.8],
                            )
                            if frame_paths:
                                visual_hook = self.visual_analyzer.analyze_hook_frames(
                                    frame_paths=frame_paths,
                                    reel_code=reel.code,
                                    caption=reel.caption,
                                )
                                reel.visual_hook = visual_hook
                                logger.info(
                                    f"Gancho visual do Reel {reel.code} analisado com sucesso! "
                                    f"Síntese: '{visual_hook.visual_summary[:60]}...'"
                                )
                        except Exception as vis_exc:
                            logger.warning(f"Aviso na análise visual do Reel {reel.code}: {vis_exc}")

                except Exception as exc:
                    logger.warning(f"Não foi possível processar mídia do Reel {reel.code}: {exc}")

        finally:
            # Limpeza estrita e imediata de todos os arquivos temporários de vídeo, áudio e frames
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Arquivos temporários de vídeo, áudio e frames removidos com sucesso.")
            except Exception as exc:
                logger.debug(f"Aviso ao remover diretório temporário: {exc}")

        return reels

    def transcribe_reels_from_urls(
        self,
        urls: list[str],
        collector=None,
        status_callback: Callable[[str], None] | None = None,
    ) -> list[ReelItem]:
        """Obtém, baixa e transcreve todo o áudio de uma lista arbitrária de URLs de Reels."""
        clean_urls: list[str] = []
        seen: set[str] = set()
        for u in urls:
            cleaned = u.strip().strip("'\"")
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                clean_urls.append(cleaned)

        if not clean_urls:
            return []

        reels: list[ReelItem] = []
        for idx, u in enumerate(clean_urls, 1):
            msg = f"Obtendo dados do vídeo {idx}/{len(clean_urls)}..."
            logger.info(msg)
            if status_callback:
                status_callback(msg)

            try:
                if collector:
                    reel = collector.get_reel_by_url(u)
                else:
                    from src.instagram.collector import InstagramCollector
                    code = InstagramCollector.extract_code_from_url(u)
                    reel = ReelItem(pk="0", code=code, url=u)
                reels.append(reel)
            except Exception as exc:
                logger.warning(f"Erro ao obter metadados da URL {u}: {exc}")
                # Fallback criando ReelItem mínimo
                from src.instagram.collector import InstagramCollector
                code = InstagramCollector.extract_code_from_url(u)
                reels.append(ReelItem(pk="0", code=code, url=u))

        # Transcreve todos os vídeos coletados
        return self.process_top_reels(
            reels, top_n=len(reels), status_callback=status_callback
        )
