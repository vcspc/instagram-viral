"""Transcrição de áudio com timestamps e detecção de ganchos via faster-whisper."""
import logging
from pathlib import Path
from src.models.instagram import ReelTranscript, TranscriptSegment

logger = logging.getLogger(__name__)

# Patch de compatibilidade para PyAV >= 14/19 (remove argumento obsoleto 'metadata_errors')
try:
    import av
    _original_av_open = av.open

    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _original_av_open(*args, **kwargs)

    av.open = _safe_av_open
except Exception as exc:
    logger.debug(f"Aviso ao inicializar patch do PyAV: {exc}")


def format_seconds_to_timestamp(seconds: float) -> str:
    """Converte segundos float em formato MM:SS (ex: 75.2 -> 01:15)."""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


class WhisperTranscriber:
    """Transcreve arquivos de áudio utilizando faster-whisper com quantização int8."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _ensure_model_loaded(self):
        """Carrega o modelo Whisper sob demanda (lazy loading)."""
        if self._model is None:
            logger.info(
                f"Carregando modelo faster-whisper '{self.model_size}' "
                f"(device={self.device}, compute_type={self.compute_type})..."
            )
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("Modelo Whisper carregado com sucesso.")

    def transcribe(self, audio_path: Path, language: str | None = "pt") -> ReelTranscript:
        """Transcreve o arquivo de áudio e extrai segmentos com timestamps e gancho inicial.

        Por padrão, utiliza 'pt' (português brasileiro). Se for informado 'auto' ou None,
        o idioma é detectado automaticamente pelo Whisper.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")

        self._ensure_model_loaded()

        # Normaliza o idioma: 'auto', vazio ou None ativam detecção automática
        target_lang = None if language in (None, "auto", "detect", "") else str(language).lower().strip()

        # Carrega o áudio diretamente via soundfile em float32 para evitar chamadas com metadata_errors
        audio_input = str(audio_path)
        try:
            import soundfile as sf
            data, sr = sf.read(str(audio_path), dtype="float32")
            if getattr(data, "ndim", 1) > 1:
                data = data.mean(axis=1)
            audio_input = data
            logger.debug(f"Áudio carregado via soundfile como ndarray float32 (amostras: {len(data)})")
        except Exception as load_err:
            logger.debug(f"Carregamento soundfile alternativo ({load_err}). Usando caminho do arquivo diretamente...")
            audio_input = str(audio_path)

        lang_label = target_lang.upper() if target_lang else "DETECÇÃO AUTOMÁTICA"
        logger.info(f"Transcrevendo áudio ({lang_label}): {audio_path.name}...")
        segments_generator, info = self._model.transcribe(
            audio_input,
            language=target_lang,
            beam_size=5,
            vad_filter=True,  # Filtro VAD para suprimir ruído e silêncio
        )

        segments: list[TranscriptSegment] = []
        full_text_parts: list[str] = []
        hook_parts: list[str] = []

        total_duration = float(getattr(info, "duration", 0.0) or 0.0)
        detected_lang = getattr(info, "language", "pt") or "pt"

        for seg in segments_generator:
            clean_text = seg.text.strip()
            if not clean_text:
                continue

            start_fmt = format_seconds_to_timestamp(seg.start)
            end_fmt = format_seconds_to_timestamp(seg.end)
            ts_label = f"[{start_fmt} - {end_fmt}]"

            segment_model = TranscriptSegment(
                start=round(seg.start, 2),
                end=round(seg.end, 2),
                text=clean_text,
                timestamp_formatted=ts_label,
            )
            segments.append(segment_model)
            full_text_parts.append(clean_text)

            # Isola as falas que começaram nos primeiros 3 segundos (gancho de atenção)
            if seg.start < 3.0:
                hook_parts.append(clean_text)

        full_text = " ".join(full_text_parts).strip()
        hook_text = " ".join(hook_parts).strip()

        # Se nenhum segmento começou antes de 3s mas há segmentos, usa o primeiro como gancho inicial
        if not hook_text and segments:
            hook_text = segments[0].text

        logger.info(
            f"Transcrição concluída ({len(segments)} segmentos, {total_duration:.1f}s, idioma={detected_lang})"
        )

        return ReelTranscript(
            text=full_text,
            segments=segments,
            language=detected_lang,
            duration=total_duration,
            hook_text_3s=hook_text,
        )
