"""Modelos Pydantic para Reels, Métricas e Perfis do Instagram."""
from datetime import datetime
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    pk: str = Field(description="ID numérico único do usuário no Instagram")
    username: str = Field(description="Nome de usuário (@)")
    full_name: str = Field(default="", description="Nome completo ou nome de exibição")
    biography: str = Field(default="", description="Texto completo da bio")
    follower_count: int = Field(default=0, description="Total de seguidores")
    following_count: int = Field(default=0, description="Total de perfis seguidos")
    media_count: int = Field(default=0, description="Quantidade total de publicações no feed")
    is_verified: bool = Field(default=False, description="Selo de conta verificada")
    is_business: bool = Field(default=False, description="Indica se é uma conta comercial ou profissional")
    external_url: str = Field(default="", description="Link externo presente na biografia")
    category: str = Field(default="", description="Categoria profissional do perfil")
    profile_pic_url: str = Field(default="", description="URL da foto de perfil")


class TranscriptSegment(BaseModel):
    start: float = Field(description="Segundo de início do trecho falado")
    end: float = Field(description="Segundo de término do trecho falado")
    text: str = Field(description="Texto falado no trecho")
    timestamp_formatted: str = Field(description="Formato legível de tempo: [MM:SS - MM:SS]")


class ReelTranscript(BaseModel):
    text: str = Field(default="", description="Transcrição completa consolidada")
    segments: list[TranscriptSegment] = Field(
        default_factory=list, description="Lista ordenada de trechos com timestamps"
    )
    language: str = Field(default="pt", description="Idioma detectado pelo Whisper")
    duration: float = Field(default=0.0, description="Duração total do áudio em segundos")
    hook_text_3s: str = Field(
        default="", description="Texto falado especificamente nos primeiros 3 segundos"
    )


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
    video_url: str | None = Field(default=None, description="URL direta do stream de vídeo CDN")
    transcript: ReelTranscript | None = Field(default=None, description="Transcrição completa com timestamps")
    metrics: ReelMetrics = Field(default_factory=ReelMetrics)
    source_term: str = Field(default="", description="Hashtag ou termo de busca que originou a coleta")
