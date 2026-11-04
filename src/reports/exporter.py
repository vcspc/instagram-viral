"""Exportação consolidada dos resultados para Markdown, CSV e JSON."""
import csv
import json
from datetime import datetime
from pathlib import Path
from src.models.agent import ProfileAnalysis, SearchStrategy, ViralAnalysis
from src.models.instagram import ReelItem, UserProfile
from src.reports.formatters import format_number, slugify


class ReportExporter:
    """Gera e salva relatórios detalhados nos formatos MD, CSV e JSON."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        query: str,
        strategy: SearchStrategy,
        reels: list[ReelItem],
        analysis: ViralAnalysis | None = None,
        timeframe_desc: str = "Todo o período",
    ) -> dict[str, Path]:
        """Exporta os relatórios de busca nos três formatos e retorna os caminhos dos arquivos."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{slugify(query)}_{timestamp}"

        md_path = self.export_markdown(base_name, query, strategy, reels, analysis, timeframe_desc)
        csv_path = self.export_csv(base_name, reels)
        json_path = self.export_json(base_name, query, strategy, reels, analysis, timeframe_desc)

        return {"markdown": md_path, "csv": csv_path, "json": json_path}

    def export_profile_all(
        self,
        profile: UserProfile,
        reels: list[ReelItem],
        analysis: ProfileAnalysis | None = None,
        timeframe_desc: str = "Todo o período",
    ) -> dict[str, Path]:
        """Exporta os relatórios de auditoria de perfil com transcrições nos três formatos."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{slugify(profile.username)}_profile_{timestamp}"

        md_path = self.export_profile_markdown(base_name, profile, reels, analysis, timeframe_desc)
        csv_path = self.export_profile_csv(base_name, reels)
        json_path = self.export_profile_json(base_name, profile, reels, analysis, timeframe_desc)

        return {"markdown": md_path, "csv": csv_path, "json": json_path}

    def export_transcriptions_markdown(
        self,
        reels: list[ReelItem],
        language: str = "pt",
        whisper_model: str = "base",
    ) -> Path:
        """Gera um arquivo Markdown dedicado com todas as transcrições literais dos Reels enviados."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.output_dir / f"transcricoes_{timestamp}.md"

        transcribed = [r for r in reels if r.transcript]
        total_duration = sum((r.transcript.duration for r in transcribed if r.transcript), 0.0)
        total_mins = int(total_duration // 60)
        total_secs = int(total_duration % 60)

        lines = [
            "# Transcrições Literais de Reels do Instagram",
            f"\n> **Data de Geração:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"> **Total de Vídeos Enviados:** {len(reels)} ({len(transcribed)} transcritos com sucesso)",
            f"> **Tempo Total de Áudio:** {total_mins:02d}m {total_secs:02d}s",
            f"> **Idioma do Whisper:** {language.upper()}",
            f"> **Modelo Whisper Utilizado:** {whisper_model}\n",
            "---",
            "## Índice dos Vídeos Transcritos\n",
        ]

        for idx, r in enumerate(transcribed, 1):
            dur = r.transcript.duration if r.transcript else r.duration
            m = int(dur // 60)
            s = int(dur % 60)
            user_lbl = f" (@{r.author_username})" if r.author_username else ""
            lines.append(f"{idx}. [{r.code}{user_lbl}](#{idx}-reel-{r.code.lower()}) — {m:02d}:{s:02d}")

        lines.extend(["\n---", "## Transcrições Completas Detalhadas\n"])

        for idx, r in enumerate(reels, 1):
            t = r.transcript
            date_str = r.taken_at.strftime("%d/%m/%Y") if r.taken_at else "-"
            creator_str = f" • Criador: @{r.author_username}" if r.author_username else ""
            dur_str = (
                f"{int(t.duration // 60):02d}m {int(t.duration % 60):02d}s"
                if t
                else f"{int(r.duration // 60):02d}m {int(r.duration % 60):02d}s"
            )

            lines.extend([
                f"### {idx}. Reel: [{r.code}]({r.url})",
                f"- **Link Direto:** {r.url}",
                f"- **Metadados:** Duração: {dur_str} • Data: {date_str}{creator_str}",
            ])

            if r.caption:
                clean_cap = r.caption.replace("\n", " ").replace("\r", " ")[:200]
                lines.append(f"- **Legenda Original:**\n  > {clean_cap}...\n")

            if t:
                lines.extend([
                    "#### Transcrição Literal Completa:",
                    f"> {t.text}\n",
                    "#### Transcrição com Marcadores de Tempo (Timestamps):",
                    "```text",
                    *[f"{seg.timestamp_formatted} {seg.text}" for seg in t.segments],
                    "```\n",
                ])
            else:
                lines.append("> *Aviso: Não foi possível extrair a faixa de áudio deste vídeo.*\n")

            lines.append("---\n")

        file_path.write_text("\n".join(lines), encoding="utf-8")
        return file_path

    def export_markdown(
        self,
        base_name: str,
        query: str,
        strategy: SearchStrategy,
        reels: list[ReelItem],
        analysis: ViralAnalysis | None,
        timeframe_desc: str = "Todo o período",
    ) -> Path:
        """Gera um relatório executivo em Markdown com links clicáveis."""
        file_path = self.output_dir / f"{base_name}.md"

        lines = [
            f"# Relatório de Descoberta: Reels Virais no Instagram",
            f"\n> **Tema Pesquisado:** *{query}*",
            f"> **Filtro de Período:** {timeframe_desc}",
            f"> **Data de Geração:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"> **Total de Reels Analisados:** {len(reels)}\n",
            "---",
            "## 1. Estratégia Desenvolvida pelo Agente Gemini\n",
            f"**Entendimento do Nicho:**\n{strategy.intent_summary}\n",
            f"**Hashtags Primárias:** `{'`, `'.join('#' + h for h in strategy.primary_hashtags)}`\n",
            f"**Hashtags de Cauda Longa:** `{'`, `'.join('#' + h for h in strategy.long_tail_hashtags)}`\n",
            f"**Termos de Busca:** `{'`, `'.join(strategy.search_keywords)}`\n",
            f"**Justificativa Estratégica:**\n{strategy.reasoning}\n",
            "---",
        ]

        if analysis:
            lines.extend([
                "## 2. Decodificação de Viralidade (Engenharia Reversa)\n",
                "### Padrões de Ganchos (Primeiros 3 segundos):",
                *[f"- **{hook}**" for hook in analysis.common_hook_patterns],
                "\n### Temas e Formatos em Alta:",
                *[f"- {theme}" for theme in analysis.content_themes],
                "\n### Inteligência de Áudios e Discurso:",
                f"{analysis.audio_insights}\n",
                "### Estratégia de Legendas e CTA:",
                f"{analysis.caption_strategy}\n",
            ])

            if getattr(analysis, "visual_hook_patterns", None):
                lines.extend([
                    "### Padrões Visuais nos Primeiros 3 Segundos (Visão Gemini):",
                    *[f"- {vp}" for vp in analysis.visual_hook_patterns],
                    "\n",
                ])

            if getattr(analysis, "visual_recommendations", None):
                lines.extend([
                    "### Recomendações Visuais de Gravação:",
                    *[f"- {vr}" for vr in analysis.visual_recommendations],
                    "\n",
                ])

            lines.extend([
                "### Recomendações Práticas para Criadores do Nicho:",
                *[f"1. {rec}" for rec in analysis.actionable_recommendations],
                "\n---",
            ])

        # Seção de Roteiros e Ganchos dos Melhores Reels (Áudio + Visão)
        media_examined = [r for r in reels if r.transcript or r.visual_hook]
        if media_examined:
            lines.append("## 3. Roteiros e Ganchos dos Melhores Reels (Áudio Whisper & Visão Gemini)\n")
            for idx, r in enumerate(media_examined, 1):
                date_str = r.taken_at.strftime("%d/%m/%Y") if r.taken_at else "-"
                creator_str = f" - @{r.author_username}" if r.author_username else ""
                lines.extend([
                    f"### Reel #{idx}: [{r.code}]({r.url}){creator_str}",
                    f"- **Data:** {date_str} | **Duração:** {r.duration:.1f}s",
                    f"- **Views:** {format_number(r.metrics.views)} | **Likes:** {format_number(r.metrics.likes)} | **Comentários:** {format_number(r.metrics.comments)}",
                    f"- **Viral Score:** **{r.metrics.viral_score:.1f}** | **Taxa de Engajamento:** {r.metrics.engagement_rate:.2f}%\n",
                ])

                if r.visual_hook:
                    v = r.visual_hook
                    lines.extend([
                        f"> **Gancho Visual (0s a 3s - Visão Gemini):** *\"{v.visual_summary}\"*",
                        f"> - **Cenário & Elementos:** {v.scene_elements}",
                        f"> - **Texto na Tela:** {v.on_screen_text}",
                        f"> - **Quebra de Padrão (Pattern Interrupt):** {v.pattern_interrupt}\n",
                    ])

                if r.transcript:
                    t = r.transcript
                    lines.extend([
                        f"> **Gancho Falado (0s a 3s - Whisper):** *\"{t.hook_text_3s}\"*\n",
                        "**Roteiro Falado Completo:**",
                        "```text",
                        *[f"{seg.timestamp_formatted} {seg.text}" for seg in t.segments],
                        "```\n",
                    ])
            lines.append("---\n")
            lines.append("## 4. Tabela dos Reels Mais Virais Encontrados\n")
        else:
            lines.append("## 3. Tabela dos Reels Mais Virais Encontrados\n")

        lines.extend([
            "| # | Criador | Publicado | Views | Likes | Comentários | Engajamento | Viral Score | Áudio? | Visão? | Link Direto | Origem |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ])

        for idx, reel in enumerate(reels, 1):
            views_fmt = format_number(reel.metrics.views)
            likes_fmt = format_number(reel.metrics.likes)
            comments_fmt = format_number(reel.metrics.comments)
            er_fmt = f"{reel.metrics.engagement_rate:.2f}%"
            score_fmt = f"{reel.metrics.viral_score:.1f}"
            link_md = f"[{reel.code}]({reel.url})"
            author_md = f"[@{reel.author_username}](https://www.instagram.com/{reel.author_username}/)"
            date_str = reel.taken_at.strftime("%d/%m/%Y") if reel.taken_at else "-"
            has_t = "Sim" if reel.transcript else "Não"
            has_v = "Sim" if reel.visual_hook else "Não"
            lines.append(
                f"| {idx} | {author_md} | {date_str} | {views_fmt} | {likes_fmt} | {comments_fmt} | {er_fmt} | **{score_fmt}** | {has_t} | {has_v} | {link_md} | {reel.source_term} |"
            )

        file_path.write_text("\n".join(lines), encoding="utf-8")
        return file_path

    def export_profile_markdown(
        self,
        base_name: str,
        profile: UserProfile,
        reels: list[ReelItem],
        analysis: ProfileAnalysis | None,
        timeframe_desc: str = "Todo o período",
    ) -> Path:
        """Gera relatório de auditoria de perfil em Markdown com transcrições, visão e timestamps."""
        file_path = self.output_dir / f"{base_name}.md"

        lines = [
            f"# Auditoria de Perfil e Roteiros: @{profile.username}",
            f"\n> **Criador:** @{profile.username} ({profile.full_name or 'Sem nome informado'})",
            f"> **Seguidores:** {format_number(profile.follower_count)} ({profile.follower_count:,}) | **Seguindo:** {profile.following_count:,} | **Publicações:** {profile.media_count:,}",
            f"> **Categoria:** {profile.category or 'Geral'} | **Verificado:** {'Sim' if profile.is_verified else 'Não'}",
            f"> **Filtro de Período:** {timeframe_desc}",
            f"> **Data de Geração:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n",
            "### Biografia Atual:",
            f"```text\n{profile.biography or 'Sem biografia'}\n```",
        ]

        if profile.external_url:
            lines.append(f"**Link na Bio:** [{profile.external_url}]({profile.external_url})\n")

        lines.append("---\n")

        if analysis:
            pos = analysis.positioning
            spoken = analysis.spoken_scripts
            lines.extend([
                "## 1. Diagnóstico de Posicionamento e Bio (IA Gemini)\n",
                f"- **Proposta de Valor:** {pos.value_proposition_clarity}",
                f"- **Público-Alvo Identificado:** {pos.target_audience}",
                f"- **Avaliação do CTA/Link:** {pos.bio_cta_evaluation}\n",
                "### Pontos Fortes da Bio:",
                *[f"- {s}" for s in pos.bio_strengths],
                "\n### Sugestões de Melhoria na Bio:",
                *[f"- {i}" for i in pos.bio_improvements],
                "\n---\n",
                "## 2. Decodificação dos Roteiros Falados (Transcrição Whisper)\n",
                "### Padrões dos Ganchos Iniciais (0s a 3s):",
                *[f"- **{h}**" for h in spoken.first_3s_hooks_analysis],
                f"\n**Ritmo e Retenção no Discurso:**\n{spoken.speech_pacing_and_retention}\n",
                f"**Fórmula da Estrutura do Roteiro:**\n*{spoken.script_structure_formula}*\n",
                "### Chamadas para Ação Faladas (CTAs):",
                *[f"- {c}" for c in spoken.verbal_cta_patterns],
                "\n",
            ])

            if getattr(analysis, "visual_style_and_presence", None):
                lines.extend([
                    "### Presença e Estilo Visual nos Primeiros 3 Segundos (Visão Gemini):",
                    f"{analysis.visual_style_and_presence}\n",
                ])

            if getattr(analysis, "visual_hook_breakdown", None):
                lines.extend([
                    "### Decodificação dos Ganchos Visuais do Perfil:",
                    *[f"- {vh}" for vh in analysis.visual_hook_breakdown],
                    "\n",
                ])

            lines.extend([
                "### Táticas para Modelar com Originalidade:",
                *[f"1. {t}" for t in analysis.top_tactics_to_model],
                f"\n### Template de Roteiro Recomendado:\n```text\n{analysis.recommended_script_template}\n```\n",
                "---\n",
            ])

        # Seção de Roteiros e Visão dos Top Reels do Perfil
        media_examined = [r for r in reels if r.transcript or r.visual_hook]
        if media_examined:
            lines.append("## 3. Roteiros e Ganchos dos Melhores Reels (Áudio Whisper & Visão Gemini)\n")
            for idx, r in enumerate(media_examined, 1):
                date_str = r.taken_at.strftime("%d/%m/%Y") if r.taken_at else "-"
                lines.extend([
                    f"### Reel #{idx}: [{r.code}]({r.url})",
                    f"- **Data:** {date_str} | **Duração:** {r.duration:.1f}s",
                    f"- **Views:** {format_number(r.metrics.views)} | **Likes:** {format_number(r.metrics.likes)} | **Comentários:** {format_number(r.metrics.comments)}",
                    f"- **Viral Score:** **{r.metrics.viral_score:.1f}** | **Taxa de Engajamento:** {r.metrics.engagement_rate:.2f}%\n",
                ])

                if r.visual_hook:
                    v = r.visual_hook
                    lines.extend([
                        f"> **Gancho Visual (0s a 3s - Visão Gemini):** *\"{v.visual_summary}\"*",
                        f"> - **Cenário & Elementos:** {v.scene_elements}",
                        f"> - **Texto na Tela:** {v.on_screen_text}",
                        f"> - **Quebra de Padrão (Pattern Interrupt):** {v.pattern_interrupt}\n",
                    ])

                if r.transcript:
                    t = r.transcript
                    lines.extend([
                        f"> **Gancho Falado (0s a 3s - Whisper):** *\"{t.hook_text_3s}\"*\n",
                        "**Roteiro Falado Completo:**",
                        "```text",
                        *[f"{seg.timestamp_formatted} {seg.text}" for seg in t.segments],
                        "```\n",
                    ])
            lines.append("---\n")

        lines.extend([
            "## 4. Tabela de Desempenho dos Reels Analisados\n",
            "| # | Código | Publicado | Views | Likes | Comentários | Engajamento | Viral Score | Áudio? | Visão? | Link Direto |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ])

        for idx, reel in enumerate(reels, 1):
            views_fmt = format_number(reel.metrics.views)
            likes_fmt = format_number(reel.metrics.likes)
            comments_fmt = format_number(reel.metrics.comments)
            er_fmt = f"{reel.metrics.engagement_rate:.2f}%"
            score_fmt = f"{reel.metrics.viral_score:.1f}"
            date_str = reel.taken_at.strftime("%d/%m/%Y") if reel.taken_at else "-"
            has_t = "Sim" if reel.transcript else "Não"
            has_v = "Sim" if reel.visual_hook else "Não"
            link_md = f"[{reel.code}]({reel.url})"
            lines.append(
                f"| {idx} | {reel.code} | {date_str} | {views_fmt} | {likes_fmt} | {comments_fmt} | {er_fmt} | **{score_fmt}** | {has_t} | {has_v} | {link_md} |"
            )

        file_path.write_text("\n".join(lines), encoding="utf-8")
        return file_path

    def export_csv(self, base_name: str, reels: list[ReelItem]) -> Path:
        """Gera uma planilha CSV para análise em Excel ou Google Sheets."""
        file_path = self.output_dir / f"{base_name}.csv"

        fieldnames = [
            "rank",
            "code",
            "url",
            "author_username",
            "taken_at",
            "views",
            "likes",
            "comments",
            "engagement_rate_pct",
            "viral_score",
            "duration_sec",
            "has_transcription",
            "hook_text_3s",
            "full_transcription",
            "has_visual_analysis",
            "visual_hook_summary",
            "visual_pattern_interrupt",
            "visual_scene_elements",
            "visual_on_screen_text",
            "source_term",
            "caption_preview",
        ]

        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for idx, reel in enumerate(reels, 1):
                clean_caption = (reel.caption or "").replace("\n", " ").replace("\r", " ")[:200]
                has_t = bool(reel.transcript)
                hook_3s = reel.transcript.hook_text_3s if reel.transcript else ""
                full_t = reel.transcript.text if reel.transcript else ""
                has_v = bool(reel.visual_hook)
                vis_summary = reel.visual_hook.visual_summary if reel.visual_hook else ""
                vis_pi = reel.visual_hook.pattern_interrupt if reel.visual_hook else ""
                vis_scene = reel.visual_hook.scene_elements if reel.visual_hook else ""
                vis_text = reel.visual_hook.on_screen_text if reel.visual_hook else ""
                writer.writerow({
                    "rank": idx,
                    "code": reel.code,
                    "url": reel.url,
                    "author_username": reel.author_username,
                    "taken_at": reel.taken_at.isoformat() if reel.taken_at else "",
                    "views": reel.metrics.views,
                    "likes": reel.metrics.likes,
                    "comments": reel.metrics.comments,
                    "engagement_rate_pct": reel.metrics.engagement_rate,
                    "viral_score": reel.metrics.viral_score,
                    "duration_sec": reel.duration,
                    "has_transcription": has_t,
                    "hook_text_3s": hook_3s,
                    "full_transcription": full_t,
                    "has_visual_analysis": has_v,
                    "visual_hook_summary": vis_summary,
                    "visual_pattern_interrupt": vis_pi,
                    "visual_scene_elements": vis_scene,
                    "visual_on_screen_text": vis_text,
                    "source_term": reel.source_term,
                    "caption_preview": clean_caption,
                })

        return file_path

    def export_profile_csv(self, base_name: str, reels: list[ReelItem]) -> Path:
        """Gera planilha CSV com dados dos Reels do perfil incluindo transcrições e ganchos visuais."""
        file_path = self.output_dir / f"{base_name}.csv"

        fieldnames = [
            "rank",
            "code",
            "url",
            "taken_at",
            "views",
            "likes",
            "comments",
            "engagement_rate_pct",
            "viral_score",
            "duration_sec",
            "has_transcription",
            "hook_text_3s",
            "full_transcription",
            "has_visual_analysis",
            "visual_hook_summary",
            "visual_pattern_interrupt",
            "visual_scene_elements",
            "visual_on_screen_text",
            "caption_preview",
        ]

        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for idx, reel in enumerate(reels, 1):
                clean_caption = (reel.caption or "").replace("\n", " ").replace("\r", " ")[:200]
                has_t = bool(reel.transcript)
                hook_3s = reel.transcript.hook_text_3s if reel.transcript else ""
                full_t = reel.transcript.text if reel.transcript else ""
                has_v = bool(reel.visual_hook)
                vis_summary = reel.visual_hook.visual_summary if reel.visual_hook else ""
                vis_pi = reel.visual_hook.pattern_interrupt if reel.visual_hook else ""
                vis_scene = reel.visual_hook.scene_elements if reel.visual_hook else ""
                vis_text = reel.visual_hook.on_screen_text if reel.visual_hook else ""
                writer.writerow({
                    "rank": idx,
                    "code": reel.code,
                    "url": reel.url,
                    "taken_at": reel.taken_at.isoformat() if reel.taken_at else "",
                    "views": reel.metrics.views,
                    "likes": reel.metrics.likes,
                    "comments": reel.metrics.comments,
                    "engagement_rate_pct": reel.metrics.engagement_rate,
                    "viral_score": reel.metrics.viral_score,
                    "duration_sec": reel.duration,
                    "has_transcription": has_t,
                    "hook_text_3s": hook_3s,
                    "full_transcription": full_t,
                    "has_visual_analysis": has_v,
                    "visual_hook_summary": vis_summary,
                    "visual_pattern_interrupt": vis_pi,
                    "visual_scene_elements": vis_scene,
                    "visual_on_screen_text": vis_text,
                    "caption_preview": clean_caption,
                })

        return file_path

    def export_json(
        self,
        base_name: str,
        query: str,
        strategy: SearchStrategy,
        reels: list[ReelItem],
        analysis: ViralAnalysis | None,
        timeframe_desc: str = "Todo o período",
    ) -> Path:
        """Exporta os dados brutos estruturados em JSON."""
        file_path = self.output_dir / f"{base_name}.json"

        data = {
            "query": query,
            "timeframe": timeframe_desc,
            "generated_at": datetime.now().isoformat(),
            "strategy": strategy.model_dump(),
            "analysis": analysis.model_dump() if analysis else None,
            "total_reels": len(reels),
            "reels": [r.model_dump(mode="json") for r in reels],
        }

        with open(file_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return file_path

    def export_profile_json(
        self,
        base_name: str,
        profile: UserProfile,
        reels: list[ReelItem],
        analysis: ProfileAnalysis | None,
        timeframe_desc: str = "Todo o período",
    ) -> Path:
        """Exporta os dados brutos completos do perfil e transcrições em JSON."""
        file_path = self.output_dir / f"{base_name}.json"

        data = {
            "profile": profile.model_dump(),
            "timeframe": timeframe_desc,
            "generated_at": datetime.now().isoformat(),
            "analysis": analysis.model_dump() if analysis else None,
            "total_reels": len(reels),
            "reels": [r.model_dump(mode="json") for r in reels],
        }

        with open(file_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return file_path
