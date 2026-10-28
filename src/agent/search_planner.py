"""Planejamento dinâmico de pesquisa e expansão semântica via Gemini."""
import logging
from src.agent.gemini_client import GeminiClient
from src.agent.prompts import EVALUATION_SYSTEM_PROMPT, STRATEGY_SYSTEM_PROMPT
from src.models.agent import SearchEvaluation, SearchStrategy
from src.models.instagram import ReelItem

logger = logging.getLogger(__name__)


class SearchPlanner:
    """Gerencia a formulação de estratégias e o refinamento de buscas com a IA."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def plan_search(self, user_query: str) -> SearchStrategy:
        """Compreende o nicho do usuário e formula uma estratégia de hashtags e termos."""
        logger.info(f"O Agente Gemini está analisando a solicitação: '{user_query}'...")

        prompt = f"""
        O usuário deseja encontrar os vídeos de Reels mais virais e de maior engajamento para a seguinte necessidade:
        "{user_query}"

        Gere um plano de busca estruturado com:
        - Resumo do entendimento do nicho
        - 3 a 5 hashtags primárias (sem #)
        - 4 a 6 hashtags de cauda longa altamente específicas (sem #)
        - 3 a 5 palavras-chave de busca
        - Sua justificativa estratégica detalhada
        """

        return self.gemini.generate_structured(
            prompt=prompt,
            system_instruction=STRATEGY_SYSTEM_PROMPT,
            response_schema=SearchStrategy,
        )

    def evaluate_and_refine(
        self,
        current_reels: list[ReelItem],
        target_count: int,
        explored_terms: list[str],
        original_query: str,
    ) -> SearchEvaluation:
        """Avalia os resultados obtidos e decide termos adicionais se necessário."""
        total_found = len(current_reels)
        top_terms_summary = [f"{r.source_term} (views: {r.metrics.views})" for r in current_reels[:5]]

        prompt = f"""
        Objetivo inicial: "{original_query}"
        Meta de Reels desejada: {target_count}
        Reels únicos coletados até agora: {total_found}
        Termos já explorados: {', '.join(explored_terms)}
        Amostra dos Reels com melhor desempenho coletados:
        {chr(10).join(top_terms_summary) if top_terms_summary else 'Nenhum reel relevante ainda.'}

        Avalie se devemos continuar a busca para atingir a meta e proponha termos e hashtags novos (sem #).
        """

        return self.gemini.generate_structured(
            prompt=prompt,
            system_instruction=EVALUATION_SYSTEM_PROMPT,
            response_schema=SearchEvaluation,
        )
