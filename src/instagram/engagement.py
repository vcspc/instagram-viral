"""Cálculos matemáticos de engajamento e pontuação de viralidade."""
import math
from src.models.instagram import ReelMetrics, ReelItem


def calculate_metrics(views: int, likes: int, comments: int) -> ReelMetrics:
    """Calcula taxas relativas e score de viralidade balanceado.

    Fórmula do Viral Score:
    Pondera likes com peso 1.0 e comentários com peso 3.5 (comentários indicam
    alta retenção e debate no algoritmo), normalizados por escala logarítmica
    de visualizações para evitar que vídeos com poucas views e poucas interações
    tenham scores artificialmente inflados.
    """
    safe_views = max(views, 1)
    safe_likes = max(likes, 0)
    safe_comments = max(comments, 0)

    # Taxa de engajamento baseada em visualizações (%)
    engagement_rate = round(((safe_likes + safe_comments) / safe_views) * 100, 2)

    # Razão de debate (comentários por curtida)
    discussion_ratio = round(safe_comments / max(safe_likes, 1), 4)

    # Viral score ponderado
    # Interações ponderadas:
    interaction_weight = (safe_likes * 1.0) + (safe_comments * 3.5)
    # Fator logarítmico para suavizar grandes volumes:
    log_factor = math.log10(max(safe_views, 10)) + 1.0
    viral_score = round(interaction_weight / log_factor, 2)

    return ReelMetrics(
        views=views,
        likes=likes,
        comments=comments,
        engagement_rate=engagement_rate,
        discussion_ratio=discussion_ratio,
        viral_score=viral_score,
    )


def sort_reels_by_viral_score(reels: list[ReelItem]) -> list[ReelItem]:
    """Ordena a lista de Reels pelo Viral Score decrescente."""
    return sorted(reels, key=lambda r: r.metrics.viral_score, reverse=True)


def sort_reels_by_views(reels: list[ReelItem]) -> list[ReelItem]:
    """Ordena a lista de Reels pelo volume de visualizações decrescente."""
    return sorted(reels, key=lambda r: r.metrics.views, reverse=True)
