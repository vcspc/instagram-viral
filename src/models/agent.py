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


class PositioningAnalysis(BaseModel):
    value_proposition_clarity: str = Field(
        description="Clareza da proposta de valor transmitida pela bio e feed"
    )
    target_audience: str = Field(
        description="Público-alvo primário identificado no perfil"
    )
    bio_cta_evaluation: str = Field(
        description="Avaliação crítica da chamada para ação e link da bio"
    )
    bio_strengths: list[str] = Field(
        description="Pontos fortes do posicionamento atual na bio"
    )
    bio_improvements: list[str] = Field(
        description="Sugestões práticas de melhoria ou reescrita da bio para aumentar conversão"
    )


class SpokenScriptAnalysis(BaseModel):
    first_3s_hooks_analysis: list[str] = Field(
        description="Decodificação dos ganchos falados nos primeiros 3s dos reels mais virais"
    )
    speech_pacing_and_retention: str = Field(
        description="Análise do ritmo de fala, quebras de padrão e retenção ao longo dos vídeos"
    )
    verbal_cta_patterns: list[str] = Field(
        description="Padrões de chamadas para ação faladas pelo criador nos vídeos"
    )
    script_structure_formula: str = Field(
        description="Fórmula padrão de roteiro identificada (ex: Gancho -> Problema -> Solução -> CTA)"
    )


class ProfileAnalysis(BaseModel):
    positioning: PositioningAnalysis = Field(
        description="Análise do perfil, biografia e posicionamento estratégico"
    )
    reels_performance_summary: str = Field(
        description="Diagnóstico da consistência e fatores que causaram picos de visualização"
    )
    spoken_scripts: SpokenScriptAnalysis = Field(
        description="Decodificação detalhada dos roteiros falados com base nas transcrições"
    )
    top_tactics_to_model: list[str] = Field(
        description="Táticas práticas para replicar o sucesso desse perfil com originalidade"
    )
    recommended_script_template: str = Field(
        description="Template prático de roteiro inspirado no vídeo de maior desempenho do perfil"
    )
