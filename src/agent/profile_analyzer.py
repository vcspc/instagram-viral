"""Análise de perfil do Instagram e decodificação de roteiros falados via Gemini."""
import logging
from src.agent.gemini_client import GeminiClient
from src.agent.prompts import PROFILE_ANALYSIS_SYSTEM_PROMPT
from src.models.agent import ProfileAnalysis
from src.models.instagram import ReelItem, UserProfile
from src.reports.formatters import format_number

logger = logging.getLogger(__name__)


class ProfileAnalyzer:
    """Realiza a auditoria estratégica de um criador do Instagram através da IA do Gemini."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def analyze_profile(
        self,
        profile: UserProfile,
        reels: list[ReelItem],
        transcribed_reels: list[ReelItem] | None = None,
    ) -> ProfileAnalysis:
        """Examina o perfil, bio, métricas de Reels e os roteiros transcritos com timestamps."""
        logger.info(f"O Agente Gemini está auditando o perfil @{profile.username} e seus roteiros...")

        # Métricas agregadas dos Reels
        total_views = sum(r.metrics.views for r in reels)
        avg_views = total_views // max(len(reels), 1)
        avg_er = sum(r.metrics.engagement_rate for r in reels) / max(len(reels), 1)
        peak_score = max((r.metrics.viral_score for r in reels), default=0.0)

        # Monta a seção de Reels transcritos com timestamps
        transcripts_section: list[str] = []
        target_transcribed = transcribed_reels or [r for r in reels if r.transcript]

        for idx, r in enumerate(target_transcribed, 1):
            t = r.transcript
            lines = [
                f"\n[Reel Transcrito #{idx} - Código: {r.code}]",
                f"- Link: {r.url}",
                f"- Duração: {r.duration:.1f}s | Publicado em: {r.taken_at.strftime('%d/%m/%Y') if r.taken_at else '-'}",
                f"- Views: {format_number(r.metrics.views)} | Likes: {format_number(r.metrics.likes)} | Comentários: {format_number(r.metrics.comments)}",
                f"- Viral Score: {r.metrics.viral_score:.1f} | Engajamento: {r.metrics.engagement_rate:.2f}%",
                f"- Legenda: {(r.caption or '')[:200]}...",
            ]

            if t:
                lines.append(f"- GANCHO FALADO NOS PRIMEIROS 3s: \"{t.hook_text_3s}\"")
                lines.append("- ROTEIRO FALADO COMPLETO (COM TIMESTAMPS):")
                for seg in t.segments:
                    lines.append(f"  {seg.timestamp_formatted} {seg.text}")
            else:
                lines.append("- (Sem transcrição de áudio disponível)")

            transcripts_section.append("\n".join(lines))

        prompt = f"""
        AUDITORIA DO PERFIL DO INSTAGRAM: @{profile.username}
        ====================================================
        - Nome de Exibição: {profile.full_name or 'Não informado'}
        - Categoria: {profile.category or 'Geral'}
        - Verificado: {'Sim' if profile.is_verified else 'Não'} | Conta Comercial: {'Sim' if profile.is_business else 'Não'}
        - Seguidores: {format_number(profile.follower_count)} ({profile.follower_count:,})
        - Seguindo: {profile.following_count:,}
        - Total de Publicações: {profile.media_count:,}
        - Link Externo na Bio: {profile.external_url or 'Nenhum'}
        - Texto da Bio:
        \"\"\"{profile.biography}\"\"\"

        DESEMPENHO DOS REELS ANALISADOS ({len(reels)} vídeos):
        - Média de Visualizações: {format_number(avg_views)}
        - Taxa Média de Engajamento: {avg_er:.2f}%
        - Maior Viral Score Atingido: {peak_score:.1f}

        REELS DE MAIOR DESEMPENHO E SEUS ROTEIROS FALADOS TRANCRITOS:
        {''.join(transcripts_section) if transcripts_section else 'Nenhum reel transcrito.'}

        Execute a auditoria aprofundada do perfil e decodifique os roteiros falados conforme as diretrizes do sistema.
        """

        return self.gemini.generate_structured(
            prompt=prompt,
            system_instruction=PROFILE_ANALYSIS_SYSTEM_PROMPT,
            response_schema=ProfileAnalysis,
        )
