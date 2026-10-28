"""Modelos Pydantic para Reels e Métricas do Instagram."""
from datetime import datetime
from pydantic import BaseModel, Field


class ReelMetrics(BaseModel):
    views: int = Field(default=0, description="Contagem total de visualizações/plays")
    likes: int = Field(default=0, description="Contagem de curtidas")
    comments: int = Field(default=0, description="Contagem de comentários")
    engagement_rate: float = Field(
        default=0.0,
        description="Taxa de engajamento percentual baseada em views: ((likes+comments)/views)*100"
    )
    discussion_ratio: float = Field(
        default=0.0,
        description="Razão entre comentários e likes: comments/likes"
    )
    viral_score: float = Field(
        default=0.0,
        description="Score ponderado de viralidade combinando volume absoluto e taxa relativa"
    )


class ReelItem(BaseModel):
    pk: str = Field(description="ID único da mídia no Instagram")
    code: str = Field(description="Shortcode do Reel (ex: C8xY12zAbc)")
    url: str = Field(description="Link direto no formato https://www.instagram.com/reel/{code}/")
    caption: str = Field(default="", description="Legenda completa do post")
    duration: float = Field(default=0.0, description="Duração do vídeo em segundos")
    taken_at: datetime | None = Field(default=None, description="Data/hora da publicação")
    author_username: str = Field(default="", description="Nome de usuário do criador")
    metrics: ReelMetrics = Field(default_factory=ReelMetrics)
    source_term: str = Field(default="", description="Hashtag ou termo de busca que originou a coleta")
