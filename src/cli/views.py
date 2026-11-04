"""Componentes visuais e renderização de tabelas e painéis com Rich."""
import sys

# Assegura codificação UTF-8 no Windows para spinners e emojis do Rich
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from src.models.agent import ProfileAnalysis, SearchStrategy, ViralAnalysis
from src.models.instagram import ReelItem, UserProfile
from src.reports.formatters import format_number

console = Console(force_terminal=True)


def render_banner() -> None:
    """Exibe o cabeçalho estilizado da aplicação."""
    title = Text("Instagram Viral Reels AI Agent", style="bold cyan")
    subtitle = Text(
        "Descoberta de Reels, Análise de Perfis e Transcrição via Whisper + Gemini",
        style="dim",
    )
    console.print(Panel(Text.assemble(title, "\n", subtitle), border_style="cyan"))


def render_strategy_panel(strategy: SearchStrategy) -> None:
    """Renderiza a estratégia e o raciocínio gerados pelo Gemini."""
    content = [
        f"[bold green]Compreensão da Intenção:[/bold green] {strategy.intent_summary}\n",
        f"[bold yellow]Hashtags Principais:[/bold yellow] {' '.join('#' + h for h in strategy.primary_hashtags)}",
        f"[bold magenta]Hashtags Cauda Longa:[/bold magenta] {' '.join('#' + h for h in strategy.long_tail_hashtags)}",
        f"[bold blue]Termos de Busca:[/bold blue] {', '.join(strategy.search_keywords)}\n",
        f"[dim]{strategy.reasoning}[/dim]",
    ]
    console.print(
        Panel(
            "\n".join(content),
            title="[bold cyan]Estratégia do Agente Gemini[/bold cyan]",
            border_style="green",
        )
    )


def render_profile_card(profile: UserProfile) -> None:
    """Renderiza o cartão visual com métricas cadastrais e biografia do criador."""
    verified_badge = " [bold blue]✓ Verificado[/bold blue]" if profile.is_verified else ""
    biz_badge = " [dim](Comercial)[/dim]" if profile.is_business else ""

    header = f"[bold cyan]@{profile.username}[/bold cyan]{verified_badge}{biz_badge}"
    if profile.full_name:
        header += f" • [white]{profile.full_name}[/white]"
    if profile.category:
        header += f" • [dim yellow]{profile.category}[/dim yellow]"

    metrics_line = (
        f"[bold green]Seguidores:[/bold green] {format_number(profile.follower_count)} ({profile.follower_count:,})   "
        f"[bold yellow]Seguindo:[/bold yellow] {profile.following_count:,}   "
        f"[bold magenta]Publicações:[/bold magenta] {profile.media_count:,}"
    )

    bio_text = profile.biography or "[dim]Nenhuma biografia configurada.[/dim]"
    link_line = f"\n[bold blue]Link na Bio:[/bold blue] [underline blue]{profile.external_url}[/underline blue]" if profile.external_url else ""

    body = f"{header}\n\n{metrics_line}\n\n[bold]Biografia:[/bold]\n{bio_text}{link_line}"

    console.print(
        Panel(
            body,
            title="[bold cyan]Perfil do Instagram Auditado[/bold cyan]",
            border_style="cyan",
        )
    )


def render_reels_table(reels: list[ReelItem], limit: int = 15) -> None:
    """Renderiza a tabela de Reels ranqueados pelo Score de Viralidade."""
    table = Table(
        title=f"Top {min(len(reels), limit)} Reels Mais Virais Encontrados",
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("#", style="dim", width=4, justify="center")
    table.add_column("Criador", style="bold white", width=16)
    table.add_column("Data", justify="center", style="dim", width=10)
    table.add_column("Views", justify="right", style="cyan")
    table.add_column("Likes", justify="right", style="green")
    table.add_column("Comments", justify="right", style="yellow")
    table.add_column("Taxa %", justify="right", style="magenta")
    table.add_column("Viral Score", justify="right", style="bold red")
    table.add_column("Origem", style="dim", width=14)
    table.add_column("Link", style="underline blue")

    for idx, reel in enumerate(reels[:limit], 1):
        score_style = "bold green" if idx <= 3 else "bold yellow" if idx <= 7 else "white"
        date_str = reel.taken_at.strftime("%d/%m/%Y") if reel.taken_at else "-"
        table.add_row(
            str(idx),
            f"@{reel.author_username}",
            date_str,
            format_number(reel.metrics.views),
            format_number(reel.metrics.likes),
            format_number(reel.metrics.comments),
            f"{reel.metrics.engagement_rate:.2f}%",
            f"[{score_style}]{reel.metrics.viral_score:.1f}[/{score_style}]",
            reel.source_term,
            reel.url,
        )

    console.print(table)


def render_transcripts_panel(reels: list[ReelItem]) -> None:
    """Renderiza os roteiros falados transcritos com timestamps e a análise do gancho visual."""
    examined = [r for r in reels if r.transcript or r.visual_hook]
    if not examined:
        return

    for idx, reel in enumerate(examined, 1):
        content = [
            f"[bold cyan]Link:[/bold cyan] {reel.url}  •  [bold yellow]Viral Score:[/bold yellow] {reel.metrics.viral_score:.1f}  •  [bold green]Views:[/bold green] {format_number(reel.metrics.views)}",
            f"[bold magenta]Duração:[/bold magenta] {reel.duration:.1f}s",
        ]

        if reel.visual_hook:
            v = reel.visual_hook
            content.extend([
                "",
                "[bold magenta]Gancho Visual (3 frames nos primeiros 3s - Visão Gemini):[/bold magenta]",
                f"\"{v.visual_summary}\"",
                f"[dim]• Cenário & Elementos:[/dim] {v.scene_elements}",
                f"[dim]• Texto na Tela:[/dim] {v.on_screen_text}",
                f"[dim]• Quebra de Padrão (Pattern Interrupt):[/dim] {v.pattern_interrupt}",
            ])

        if reel.transcript:
            t = reel.transcript
            content.extend([
                "",
                f"[bold green]Gancho Falado (Primeiros 3 segundos - Whisper):[/bold green]\n\"{t.hook_text_3s}\"",
                "",
                f"[bold white]Roteiro Falado com Timestamps ({t.language.upper()}):[/bold white]",
            ])
            for seg in t.segments:
                content.append(f"  [cyan]{seg.timestamp_formatted}[/cyan] {seg.text}")

        console.print(
            Panel(
                "\n".join(content),
                title=f"[bold green]Análise de Áudio & Visão #{idx}: {reel.code}[/bold green]",
                border_style="green",
            )
        )


def render_analysis_panel(analysis: ViralAnalysis) -> None:
    """Renderiza a análise qualitativa do Gemini sobre os ganchos e temas virais."""
    hooks = "\n".join(f"- {h}" for h in analysis.common_hook_patterns)
    themes = "\n".join(f"- {t}" for t in analysis.content_themes)
    recs = "\n".join(f"{i}. {r}" for i, r in enumerate(analysis.actionable_recommendations, 1))

    content = [
        "[bold cyan]Padrões de Ganchos Falados (Hooks dos Primeiros 3s):[/bold cyan]",
        f"{hooks}\n",
        "[bold yellow]Formatos e Temas Predominantes:[/bold yellow]",
        f"{themes}\n",
        "[bold magenta]Áudios e Trilhas:[/bold magenta] " + analysis.audio_insights + "\n",
        "[bold blue]Estratégia de Legendas e CTA:[/bold blue] " + analysis.caption_strategy + "\n",
    ]

    if getattr(analysis, "visual_hook_patterns", None):
        vis_patterns = "\n".join(f"- {vp}" for vp in analysis.visual_hook_patterns)
        content.append(f"[bold magenta]Padrões Visuais nos Primeiros 3s (Visão Gemini):[/bold magenta]\n{vis_patterns}\n")

    if getattr(analysis, "visual_recommendations", None):
        vis_recs = "\n".join(f"- {vr}" for vr in analysis.visual_recommendations)
        content.append(f"[bold green]Recomendações Visuais para Gravação:[/bold green]\n{vis_recs}\n")

    content.append("[bold green]Recomendações Práticas Gerais:[/bold green]\n" + recs)

    console.print(
        Panel(
            "\n".join(content),
            title="[bold green]Inteligência de Conteúdo do Gemini (Engenharia Reversa)[/bold green]",
            border_style="yellow",
        )
    )


def render_profile_analysis_panel(analysis: ProfileAnalysis) -> None:
    """Renderiza o diagnóstico aprofundado do perfil e dos roteiros transcritos."""
    pos = analysis.positioning
    spoken = analysis.spoken_scripts

    strengths = "\n".join(f"  [green]+[/green] {s}" for s in pos.bio_strengths)
    improvements = "\n".join(f"  [yellow]![/yellow] {i}" for i in pos.bio_improvements)
    hooks_3s = "\n".join(f"- {h}" for h in spoken.first_3s_hooks_analysis)
    ctas = "\n".join(f"- {c}" for c in spoken.verbal_cta_patterns)
    tactics = "\n".join(f"{i}. {t}" for i, t in enumerate(analysis.top_tactics_to_model, 1))

    content = [
        "[bold cyan]1. Diagnóstico de Posicionamento e Bio:[/bold cyan]",
        f"  [bold]Proposta de Valor:[/bold] {pos.value_proposition_clarity}",
        f"  [bold]Público-Alvo Identificado:[/bold] {pos.target_audience}",
        f"  [bold]Avaliação do CTA/Link:[/bold] {pos.bio_cta_evaluation}\n",
        "[bold green]Pontos Fortes da Bio:[/bold green]",
        f"{strengths}\n",
        "[bold yellow]Sugestões de Melhoria da Bio:[/bold yellow]",
        f"{improvements}\n",
        "---",
        "[bold cyan]2. Análise dos Roteiros Falados Transcritos (Whisper):[/bold cyan]",
        f"[bold]Padrão dos Ganchos (Primeiros 3s):[/bold]\n{hooks_3s}\n",
        f"[bold]Ritmo e Retenção no Discurso:[/bold] {spoken.speech_pacing_and_retention}\n",
        f"[bold]Fórmula de Estrutura do Roteiro:[/bold] [italic]{spoken.script_structure_formula}[/italic]\n",
        f"[bold]Chamadas para Ação Faladas (CTAs):[/bold]\n{ctas}\n",
        "---",
    ]

    if getattr(analysis, "visual_style_and_presence", None):
        content.extend([
            "[bold cyan]3. Análise Visual e Estética nos Primeiros 3s (Visão Gemini):[/bold cyan]",
            f"{analysis.visual_style_and_presence}\n",
        ])
        if getattr(analysis, "visual_hook_breakdown", None):
            v_breaks = "\n".join(f"- {vb}" for vb in analysis.visual_hook_breakdown)
            content.append(f"[bold]Decodificação dos Ganchos Visuais:[/bold]\n{v_breaks}\n")
        content.append("---")

    content.extend([
        "[bold cyan]Desempenho e Consistência dos Reels:[/bold cyan]",
        f"{analysis.reels_performance_summary}\n",
        "---",
        "[bold cyan]Táticas para Modelar com Originalidade:[/bold cyan]",
        f"{tactics}\n",
        "---",
        "[bold green]Template Prático de Roteiro Recomendado:[/bold green]",
        f"[italic yellow]{analysis.recommended_script_template}[/italic yellow]",
    ])

    console.print(
        Panel(
            "\n".join(content),
            title="[bold green]Diagnóstico Completo de Perfil e Roteiros (IA Gemini)[/bold green]",
            border_style="green",
        )
    )
