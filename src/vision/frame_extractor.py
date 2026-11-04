"""Extração de frames dos 3 primeiros segundos de vídeos via FFmpeg."""
import logging
import subprocess
import sys
from pathlib import Path
from src.audio.converter import AudioConverter

logger = logging.getLogger(__name__)


class FrameExtractor:
    """Extrai frames pontuais de vídeos MP4 nos primeiros 3 segundos usando FFmpeg."""

    def __init__(self, ffmpeg_path: str | None = None):
        self.converter_helper = AudioConverter(ffmpeg_path=ffmpeg_path)
        self.ffmpeg_bin = self.converter_helper.ffmpeg_bin

    def extract_hook_frames(
        self,
        video_path: Path,
        output_dir: Path | None = None,
        timestamps: list[float] | None = None,
    ) -> list[Path]:
        """Extrai 3 frames representativos dos primeiros 3 segundos do vídeo (gancho visual)."""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Arquivo de vídeo não encontrado: {video_path}")

        target_dir = Path(output_dir) if output_dir else video_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        # Captura 3 momentos chave nos 3 primeiros segundos (início, meio e transição)
        ts_list = timestamps or [0.8, 1.8, 2.8]
        extracted_paths: list[Path] = []

        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        for i, ts in enumerate(ts_list, 1):
            frame_filename = f"{video_path.stem}_frame_{i}_{ts}s.jpg"
            frame_path = target_dir / frame_filename

            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-ss", str(ts),
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "2",  # Alta qualidade JPEG
                str(frame_path),
            ]

            logger.debug(f"Extraindo frame #{i} em {ts}s: {' '.join(cmd)}")
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=creation_flags,
                    text=True,
                )
                if res.returncode == 0 and frame_path.exists() and frame_path.stat().st_size > 0:
                    extracted_paths.append(frame_path)
                else:
                    logger.debug(f"Aviso ao extrair frame em {ts}s para {video_path.name}: {res.stderr[:200]}")
            except Exception as exc:
                logger.warning(f"Erro ao extrair frame em {ts}s: {exc}")

        logger.info(f"Extraídos {len(extracted_paths)} frames dos primeiros 3s de {video_path.name}")
        return extracted_paths
