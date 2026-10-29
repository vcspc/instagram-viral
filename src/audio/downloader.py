"""Download de vídeos dos Reels do Instagram para processamento de áudio."""
import logging
from pathlib import Path
import requests
from instagrapi import Client
from src.models.instagram import ReelItem

logger = logging.getLogger(__name__)


class ReelDownloader:
    """Realiza o download de vídeos dos Reels via CDN direto ou fallback pelo instagrapi."""

    def __init__(self, client: Client | None = None):
        self.client = client

    def download_video(self, reel: ReelItem, target_dir: Path) -> Path:
        """Baixa o vídeo de um Reel e retorna o caminho do arquivo .mp4 salvo."""
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        output_file = target_dir / f"reel_{reel.code}.mp4"

        # 1. Estratégia preferencial: download direto via streaming do CDN (evita bater na API do Instagram)
        if reel.video_url:
            try:
                logger.info(f"Baixando vídeo do Reel {reel.code} diretamente via CDN...")
                response = requests.get(
                    reel.video_url,
                    stream=True,
                    timeout=30,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )
                response.raise_for_status()

                with open(output_file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f.write(chunk)

                if output_file.exists() and output_file.stat().st_size > 1024:
                    logger.info(f"Download concluído via CDN: {output_file.name} ({output_file.stat().st_size} bytes)")
                    return output_file
            except Exception as exc:
                logger.warning(f"Download via CDN falhou para {reel.code}: {exc}. Tentando fallback do instagrapi...")

        # 2. Estratégia de Fallback: clip_download do instagrapi
        if self.client:
            try:
                logger.info(f"Recorrendo ao clip_download do instagrapi para {reel.code} (PK: {reel.pk})...")
                downloaded_path = self.client.clip_download(int(reel.pk), folder=target_dir)
                if downloaded_path and Path(downloaded_path).exists():
                    return Path(downloaded_path)
            except Exception as exc:
                logger.error(f"Fallback clip_download falhou para {reel.code}: {exc}")

        raise RuntimeError(f"Não foi possível baixar o vídeo do Reel {reel.code}.")
