"""Modelos de dados estruturados para o Agente Gemini."""
from pydantic import BaseModel, Field


class SearchStrategy(BaseModel):
    intent_summary: str = Field(
        description="Resumo da compreensão da intenção do usuário e do nicho"
    )
    primary_hashtags: list[str] = Field(
        description="Hashtags de alta densidade e mais relevantes no nicho (sem o símbolo #)"
    )
    long_tail_hashtags: list[str] = Field(
        description="Hashtags de cauda longa, nichadas e menos concorridas (sem o símbolo #)"
    )
    search_keywords: list[str] = Field(
        description="Termos de pesquisa semântica para descoberta textual de tags e criadores"
    )
    reasoning: str = Field(
        description="Justificativa estratégica para a escolha dos termos e público-alvo"
    )


class SearchEvaluation(BaseModel):
    relevance_score: float = Field(
        description="Nota de relevância dos resultados encontrados nesta rodada (0.0 a 1.0)"
    )
    should_continue: bool = Field(
        description="Se o agente deve continuar buscando termos adicionais"
    )
    new_terms_to_try: list[str] = Field(
        default_factory=list,
        description="Termos e hashtags novos ou adjacentes para a próxima rodada"
    )
    adjustment_notes: str = Field(
        default="",
        description="Observações sobre o ajuste de rota ou motivos de continuação"
    )


class ViralAnalysis(BaseModel):
    common_hook_patterns: list[str] = Field(
        description="Padrões de ganchos visuais e verbais identificados nos primeiros 3 segundos"
    )
    content_themes: list[str] = Field(
        description="Temas e formatos recorrentes que impulsionaram a retenção e compartilhamento"
    )
    audio_insights: str = Field(
        description="Observações sobre uso de áudios em alta ou narração própria"
    )
    caption_strategy: str = Field(
        description="Padrão das legendas, uso de palavras-chave e chamadas para ação (CTAs)"
    )
    actionable_recommendations: list[str] = Field(
        description="Recomendações práticas e acionáveis para o usuário replicar o sucesso"
    )
