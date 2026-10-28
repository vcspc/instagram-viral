"""Componentes visuais e renderização de tabelas e painéis com Rich."""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from src.models.agent import SearchStrategy, ViralAnalysis
from src.models.instagram import ReelItem
from src.reports.formatters import format_number

console = Console()


def render_banner() -> None:
    """Exibe o cabeçalho estilizado da aplicação."""
    title = Text("Instagram Viral Reels AI Agent", style="bold cyan")
    subtitle = Text("Descoberta e Engenharia Reversa de Conteúdo Viral via Gemini + instagrapi", style="dim")
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
