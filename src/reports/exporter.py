"""Exportação consolidada dos resultados para Markdown, CSV e JSON."""
import csv
import json
from datetime import datetime
from pathlib import Path
from src.models.agent import SearchStrategy, ViralAnalysis
from src.models.instagram import ReelItem
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
        """Exporta os relatórios nos três formatos e retorna os caminhos dos arquivos."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{slugify(query)}_{timestamp}"

        md_path = self.export_markdown(base_name, query, strategy, reels, analysis, timeframe_desc)
        csv_path = self.export_csv(base_name, reels)
        json_path = self.export_json(base_name, query, strategy, reels, analysis, timeframe_desc)

        return {"markdown": md_path, "csv": csv_path, "json": json_path}

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
                "\n### Inteligência de Áudios:",
                f"{analysis.audio_insights}\n",
                "### Estratégia de Legendas e CTA:",
                f"{analysis.caption_strategy}\n",
                "### Recomendações Práticas para Criadores:",
                *[f"1. {rec}" for rec in analysis.actionable_recommendations],
                "\n---",
            ])

        lines.extend([
            "## 3. Tabela dos Reels Mais Virais Encontrados\n",
            "| # | Criador | Publicado | Views | Likes | Comentários | Engajamento | Viral Score | Link Direto | Origem |",
            "|---|---|---|---|---|---|---|---|---|---|",
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
            lines.append(
                f"| {idx} | {author_md} | {date_str} | {views_fmt} | {likes_fmt} | {comments_fmt} | {er_fmt} | **{score_fmt}** | {link_md} | {reel.source_term} |"
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
            "source_term",
            "caption_preview",
        ]

        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for idx, reel in enumerate(reels, 1):
                clean_caption = (reel.caption or "").replace("\n", " ").replace("\r", " ")[:200]
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
                    "source_term": reel.source_term,
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
