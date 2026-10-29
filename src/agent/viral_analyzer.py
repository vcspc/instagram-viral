"""Análise qualitativa e engenharia reversa de viralidade dos Top Reels."""
import logging
from src.agent.gemini_client import GeminiClient
from src.agent.prompts import VIRAL_ANALYSIS_SYSTEM_PROMPT
from src.models.agent import ViralAnalysis
from src.models.instagram import ReelItem

logger = logging.getLogger(__name__)


class ViralAnalyzer:
    """Extrai padrões de sucesso, ganchos e estratégias dos melhores Reels minerados."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def analyze_top_reels(self, top_reels: list[ReelItem], niche_topic: str) -> ViralAnalysis:
        """Examina os Top Reels e extrai inteligência de conteúdo acionável."""
        if not top_reels:
            raise ValueError("Nenhum Reel fornecido para análise.")

        logger.info(f"O Agente Gemini está decodificando os {len(top_reels)} Reels mais virais...")

        reels_data = []
        for i, reel in enumerate(top_reels, 1):
            reel_lines = [
                f"[Reel #{i}]",
                f"- Link: {reel.url}",
                f"- Criador: @{reel.author_username}",
                f"- Duração: {reel.duration:.1f}s",
                f"- Views: {reel.metrics.views} | Likes: {reel.metrics.likes} | Comentários: {reel.metrics.comments}",
                f"- Score Viral: {reel.metrics.viral_score} | Taxa Engajamento: {reel.metrics.engagement_rate}%",
                f"- Legenda: {(reel.caption or '')[:350]}...",
            ]

            if reel.transcript:
                t = reel.transcript
                reel_lines.append(f"- GANCHO FALADO (0s a 3s): \"{t.hook_text_3s}\"")
                reel_lines.append("- ROTEIRO FALADO COM TIMESTAMPS:")
                for seg in t.segments:
                    reel_lines.append(f"  {seg.timestamp_formatted} {seg.text}")

            reels_data.append("\n".join(reel_lines))

        prompt = f"""
        Nicho pesquisado: "{niche_topic}"

        Abaixo estão os dados reais dos Reels com maior engajamento e viralidade encontrados no Instagram:

        {chr(10).join(reels_data)}

        Faça a engenharia reversa desses vídeos e produza o relatório estruturado de inteligência de conteúdo.
        """

        return self.gemini.generate_structured(
            prompt=prompt,
            system_instruction=VIRAL_ANALYSIS_SYSTEM_PROMPT,
            response_schema=ViralAnalysis,
        )
