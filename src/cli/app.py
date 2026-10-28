"""Comandos de linha de comando da aplicação com Typer."""
import logging
from pathlib import Path
import typer
from instagrapi.exceptions import ClientUnauthorizedError, LoginRequired
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.agent.gemini_client import GeminiClient
from src.agent.search_planner import SearchPlanner
from src.agent.viral_analyzer import ViralAnalyzer
from src.config.logging_config import setup_logging
from src.config.settings import settings
from src.instagram.collector import InstagramCollector
from src.instagram.engagement import sort_reels_by_viral_score
from src.instagram.rate_limiter import RateLimiter
from src.instagram.session_manager import InstagramSessionManager
from src.models.instagram import ReelItem
from src.reports.exporter import ReportExporter
from src.cli.views import (
    console,
    render_analysis_panel,
    render_banner,
    render_reels_table,
    render_strategy_panel,
)

app = typer.Typer(
    help="Instagram Viral Reels AI Agent - Descoberta de Reels virais com instagrapi e IA do Gemini."
)


@app.command()
def login(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Ativa logs detalhados.")
) -> None:
    """Efetua o primeiro login no Instagram e salva a sessão em disco."""
    setup_logging(level=logging.DEBUG if verbose else logging.INFO)
    render_banner()

    if not settings.instagram_sessionid and (not settings.instagram_username or not settings.instagram_password):
        console.print(
            "[bold red]Erro:[/bold red] Configure `INSTAGRAM_SESSIONID` (recomendado) ou `INSTAGRAM_USERNAME` e `INSTAGRAM_PASSWORD` no arquivo .env."
        )
        raise typer.Exit(code=1)

    user_label = f"@{settings.instagram_username}" if settings.instagram_username else "cookie de sessão"
    console.print(f"Iniciando autenticação para [bold cyan]{user_label}[/bold cyan]...")
    session_mgr = InstagramSessionManager(
        username=settings.instagram_username,
        password=settings.instagram_password,
        session_dir=settings.instagram_session_dir,
        sessionid=settings.instagram_sessionid,
        two_factor_seed=settings.instagram_2fa_seed,
        proxy=settings.instagram_proxy,
    )

    try:
        session_mgr.get_authenticated_client()
        console.print("[bold green]Login efetuado e sessão persistida com sucesso![/bold green]")
    except Exception as exc:
        console.print(f"[bold red]Falha no login:[/bold red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def search(
    query: str = typer.Option(..., "--query", "-q", help="Intenção ou nicho de pesquisa em linguagem natural."),
    limit: int = typer.Option(20, "--limit", "-l", help="Quantidade desejada de Reels únicos analisados."),
    rounds: int = typer.Option(2, "--rounds", "-r", help="Número máximo de rodadas de expansão pelo agente."),
    no_analysis: bool = typer.Option(False, "--no-analysis", help="Pula a análise qualitativa final do Gemini."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Exibe logs detalhados de depuração."),
) -> None:
    """Pesquisa Reels em qualquer nicho, orquestrado pela IA do Gemini."""
    setup_logging(level=logging.DEBUG if verbose else logging.INFO)
    render_banner()

    # Validação de credenciais
    if not settings.gemini_api_key:
        console.print(
            "[bold red]Erro:[/bold red] Preencha `GEMINI_API_KEY` no seu arquivo .env com a chave do Google AI Studio."
        )
        raise typer.Exit(code=1)

    if not settings.instagram_sessionid and (not settings.instagram_username or not settings.instagram_password):
        console.print(
            "[bold red]Erro:[/bold red] Configure `INSTAGRAM_SESSIONID` (recomendado) ou `INSTAGRAM_USERNAME` e `INSTAGRAM_PASSWORD` no arquivo .env."
        )
        raise typer.Exit(code=1)

    # 1. Autenticação no Instagram
    console.print("[dim]Conectando ao Instagram...[/dim]")
    session_mgr = InstagramSessionManager(
        username=settings.instagram_username,
        password=settings.instagram_password,
        session_dir=settings.instagram_session_dir,
        sessionid=settings.instagram_sessionid,
        two_factor_seed=settings.instagram_2fa_seed,
        proxy=settings.instagram_proxy,
    )
    try:
        client = session_mgr.get_authenticated_client()
    except (LoginRequired, ClientUnauthorizedError, RuntimeError) as exc:
        console.print(f"\n[bold red]Erro de autenticação no Instagram:[/bold red]\n{exc}\n")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[bold red]Erro inesperado na conexão com o Instagram:[/bold red] {exc}")
        raise typer.Exit(code=1)

    # 2. Inicialização do Agente Gemini
    gemini_client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
    planner = SearchPlanner(gemini_client=gemini_client)
    analyzer = ViralAnalyzer(gemini_client=gemini_client)
    rate_limiter = RateLimiter(delay_min=settings.request_delay_min, delay_max=settings.request_delay_max)
    collector = InstagramCollector(client=client, rate_limiter=rate_limiter)
    exporter = ReportExporter(output_dir=settings.outputs_dir)

    # 3. Fase de Planejamento da Busca
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task(description="O Agente Gemini está desenhando a estratégia de busca...", total=None)
        strategy = planner.plan_search(query)

    render_strategy_panel(strategy)

    # 4. Loop de Coleta Inteligente com instagrapi
    all_reels: list[ReelItem] = []
    explored_terms: list[str] = []

    # Fila de busca inicial balanceada: termo do usuário + palavras-chave + hashtags
    initial_search_items = []
    # 1. Termo principal informado pelo usuário
    initial_search_items.append({"type": "keyword", "value": query})
    # 2. Palavras-chave sugeridas pelo Gemini
    for kw in strategy.search_keywords:
        initial_search_items.append({"type": "keyword", "value": kw})
    # 3. Hashtags principais e de cauda longa
    for tag in strategy.primary_hashtags + strategy.long_tail_hashtags:
        initial_search_items.append({"type": "hashtag", "value": tag})

    current_queue = initial_search_items

    for current_round in range(1, rounds + 1):
        console.print(f"\n[bold cyan]Iniciando Rodada {current_round}/{rounds} de Coleta...[/bold cyan]")

        for item in current_queue:
            if len(all_reels) >= limit:
                break

            term_val = item["value"].strip()
            term_type = item["type"]
            term_key = f"{term_type}:{term_val.lower()}"

            if term_key in explored_terms or not term_val:
                continue

            explored_terms.append(term_key)
            needed = max(5, limit - len(all_reels) + 5)

            try:
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                    if term_type == "keyword":
                        progress.add_task(description=f"Pesquisando Reels por busca textual: '{term_val}'...", total=None)
                        reels_found = collector.search_reels_by_keyword(term_val, amount=min(15, needed))
                        label = f"busca:'{term_val}'"
                    else:
                        progress.add_task(description=f"Pesquisando Reels na hashtag #{term_val}...", total=None)
                        reels_found = collector.search_reels_by_hashtag(term_val, amount=min(15, needed))
                        label = f"#{term_val}"
            except (LoginRequired, ClientUnauthorizedError):
                console.print(
                    "\n[bold red]Sessão Expirada no Instagram (LoginRequired):[/bold red]\n"
                    "A sua sessão foi invalidada pelo Instagram durante a busca.\n\n"
                    "[bold yellow]Como resolver em 30 segundos:[/bold yellow]\n"
                    "1. Abra o Instagram no navegador (onde sua conta está conectada).\n"
                    "2. Pressione F12 -> aba Aplicativo (ou Armazenamento) -> Cookies -> https://www.instagram.com\n"
                    "3. Copie o valor atual do cookie 'sessionid' (certifique-se de NÃO fazer logout no navegador).\n"
                    "4. Atualize o INSTAGRAM_SESSIONID no seu arquivo .env e execute novamente.\n"
                )
                raise typer.Exit(code=1)

            all_reels.extend(reels_found)
            status_color = "green" if reels_found else "yellow"
            console.print(f"  [{status_color}]+[/{status_color}] {label}: [bold]{len(reels_found)}[/bold] Reels minerados (Total acumulado: [cyan]{len(all_reels)}[/cyan])")

        if len(all_reels) >= limit or current_round == rounds:
            break

        # O Agente avalia os resultados e ajusta a rota
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task(description="Gemini avaliando dados preliminares para próxima rodada...", total=None)
            evaluation = planner.evaluate_and_refine(
                current_reels=all_reels,
                target_count=limit,
                explored_terms=[t.split(":", 1)[-1] for t in explored_terms],
                original_query=query,
            )

        if not evaluation.should_continue or not evaluation.new_terms_to_try:
            console.print("[dim]O Agente considerou a cobertura atual satisfatória.[/dim]")
            break

        console.print(f"[yellow]Ajuste de Rota do Agente:[/yellow] {evaluation.adjustment_notes}")
        current_queue = []
        for new_term in evaluation.new_terms_to_try:
            if new_term.startswith("#"):
                current_queue.append({"type": "hashtag", "value": new_term.lstrip("#")})
            else:
                current_queue.append({"type": "keyword", "value": new_term})

    if not all_reels:
        console.print("[bold red]Nenhum Reel foi encontrado para os termos pesquisados. Tente uma busca com termos mais amplos.[/bold red]")
        raise typer.Exit(code=0)

    # 5. Ordenação pelo Score de Viralidade
    ranked_reels = sort_reels_by_viral_score(all_reels)

    # 6. Renderização da Tabela no Terminal
    console.print("\n")
    render_reels_table(ranked_reels, limit=min(len(ranked_reels), 15))

    # 7. Engenharia Reversa com Gemini (Top 10)
    analysis = None
    if not no_analysis and len(ranked_reels) > 0:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task(description="Gemini decodificando os ganchos e estratégias dos Top Reels...", total=None)
            try:
                analysis = analyzer.analyze_top_reels(ranked_reels[:10], niche_topic=query)
            except Exception as exc:
                console.print(f"[yellow]Aviso: Não foi possível gerar a análise qualitativa: {exc}[/yellow]")

        if analysis:
            console.print("\n")
            render_analysis_panel(analysis)

    # 8. Exportação dos Relatórios
    paths = exporter.export_all(query=query, strategy=strategy, reels=ranked_reels, analysis=analysis)
    console.print("\n[bold green]Relatórios gerados com sucesso:[/bold green]")
    console.print(f"  [cyan]Markdown:[/cyan] {paths['markdown']}")
    console.print(f"  [cyan]Planilha CSV:[/cyan] {paths['csv']}")
    console.print(f"  [cyan]JSON Estruturado:[/cyan] {paths['json']}")
    console.print("\n[dim]Abra o arquivo Markdown para visualizar todos os links clicáveis dos Reels.[/dim]\n")
