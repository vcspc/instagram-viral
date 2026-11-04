"""Análise multimodal de ganchos visuais nos 3 primeiros segundos via Gemini Vision."""
import logging
from pathlib import Path
from google.genai import types
from src.agent.gemini_client import GeminiClient
from src.models.instagram import VisualHookAnalysis

logger = logging.getLogger(__name__)

VISUAL_HOOK_SYSTEM_PROMPT = """Você é um especialista em psicologia da atenção, design visual de vídeo curto e engenharia reversa de ganchos (pattern interrupt) no Instagram Reels e TikTok.
Sua missão é analisar os 3 frames fotográficos capturados consecutivamente nos primeiros 3 segundos de um Reel (aproximadamente em 0.8s, 1.8s e 2.8s) e decodificar a estratégia visual que impede o usuário de rolar o feed.

Diretrizes:
1. Síntese do Gancho Visual: Explique em 1 a 2 frases por que esses 3 primeiros segundos chamam a atenção visualmente.
2. Elementos em Cena: Descreva detalhadamente o que está visível (cenário, iluminação, enquadramento como close/plano médio/selfie, expressões faciais, objetos ou produtos em destaque).
3. Textos na Tela: Identifique textos sobrepostos, títulos chamativos, stickers, setas ou legendas grafadas diretamente no vídeo nos primeiros 3s (ou indique explicitamente 'Nenhum texto na tela').
4. Quebra de Padrão (Pattern Interrupt): Identifique qual dinamismo visual ocorre entre os 3 frames (mudança brusca, movimento acelerado, expressão de choque/curiosidade, corte rápido, ação surpreendente).
"""


class VisualHookAnalyzer:
    """Analisa frames do gancho visual de Reels utilizando visão computacional da IA do Gemini."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def analyze_hook_frames(
        self,
        frame_paths: list[Path],
        reel_code: str = "",
        caption: str = "",
    ) -> VisualHookAnalysis:
        """Analisa os 3 frames dos primeiros 3 segundos de um Reel e retorna a decodificação visual."""
        if not frame_paths:
            raise ValueError("Nenhum frame fornecido para análise visual.")

        logger.info(f"O Gemini Vision está analisando {len(frame_paths)} frames do gancho do Reel {reel_code}...")

        # Monta os inputs multimodais com as imagens JPEG
        contents: list = []
        for i, f_path in enumerate(frame_paths, 1):
            if f_path.exists():
                img_bytes = f_path.read_bytes()
                part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
                contents.append(part)

        if not contents:
            raise RuntimeError("Não foi possível carregar os bytes dos frames para análise visual.")

        prompt_text = f"""
        ANÁLISE DE GANCHO VISUAL (PRIMEIROS 3 SEGUNDOS):
        Reel: {reel_code}
        Legenda do post (contexto): \"{caption[:250]}\"

        Acima estão os 3 frames capturados em sequência durante os 3 primeiros segundos do vídeo (0.8s, 1.8s e 2.8s).
        Decodifique a estratégia visual utilizada pelo criador para capturar a atenção imediata do público.
        """
        contents.append(prompt_text)

        return self.gemini.generate_structured(
            prompt=contents,
            system_instruction=VISUAL_HOOK_SYSTEM_PROMPT,
            response_schema=VisualHookAnalysis,
        )
