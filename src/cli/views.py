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
    """Renderiza os roteiros falados transcritos com marcadores de timestamp."""
    transcribed = [r for r in reels if r.transcript]
    if not transcribed:
        return

    for idx, reel in enumerate(transcribed, 1):
        t = reel.transcript
        assert t is not None

        content = [
            f"[bold cyan]Link:[/bold cyan] {reel.url}  •  [bold yellow]Viral Score:[/bold yellow] {reel.metrics.viral_score:.1f}  •  [bold green]Views:[/bold green] {format_number(reel.metrics.views)}",
            f"[bold magenta]Duração:[/bold magenta] {t.duration:.1f}s  •  [bold blue]Idioma:[/bold blue] {t.language.upper()}\n",
            f"[bold green]Gancho Falado (Primeiros 3 segundos):[/bold green]\n\"{t.hook_text_3s}\"\n",
            "[bold white]Roteiro Falado com Timestamps:[/bold white]",
        ]

        for seg in t.segments:
            content.append(f"  [cyan]{seg.timestamp_formatted}[/cyan] {seg.text}")

        console.print(
            Panel(
                "\n".join(content),
                title=f"[bold green]Roteiro Transcrito #{idx} via Whisper: {reel.code}[/bold green]",
                border_style="green",
            )
        )


def render_analysis_panel(analysis: ViralAnalysis) -> None:
    """Renderiza a análise qualitativa do Gemini sobre os ganchos e temas virais."""
    hooks = "\n".join(f"- {h}" for h in analysis.common_hook_patterns)
    themes = "\n".join(f"- {t}" for t in analysis.content_themes)
    recs = "\n".join(f"{i}. {r}" for i, r in enumerate(analysis.actionable_recommendations, 1))

    content = [
        "[bold cyan]Padrões de Ganchos (Hooks dos Primeiros 3s):[/bold cyan]",
        f"{hooks}\n",
        "[bold yellow]Formatos e Temas Predominantes:[/bold yellow]",
        f"{themes}\n",
        f"[bold magenta]Áudios e Trilhas:[/bold magenta] {analysis.audio_insights}\n",
        f"[bold blue]Estratégia de Legendas e CTA:[/bold blue] {analysis.caption_strategy}\n",
        "[bold green]Recomendações Práticas:[/bold green]",
        f"{recs}",
    ]

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
        "[bold cyan]3. Desempenho e Consistência dos Reels:[/bold cyan]",
        f"{analysis.reels_performance_summary}\n",
        "---",
        "[bold cyan]4. Táticas para Modelar com Originalidade:[/bold cyan]",
        f"{tactics}\n",
        "---",
        "[bold green]5. Template Prático de Roteiro Recomendado:[/bold green]",
        f"[italic yellow]{analysis.recommended_script_template}[/italic yellow]",
    ]

    console.print(
        Panel(
            "\n".join(content),
            title="[bold green]Diagnóstico Completo de Perfil e Roteiros (IA Gemini)[/bold green]",
            border_style="green",
        )
    )
