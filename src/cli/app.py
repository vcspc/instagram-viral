"""Comandos de linha de comando da aplicação com Typer."""
import logging
from pathlib import Path
import typer
from instagrapi.exceptions import ClientUnauthorizedError, LoginRequired
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.agent.gemini_client import GeminiClient
from src.agent.profile_analyzer import ProfileAnalyzer
from src.agent.search_planner import SearchPlanner
from src.agent.viral_analyzer import ViralAnalyzer
from src.audio.manager import AudioTranscriptionManager
from src.config.logging_config import setup_logging
from src.config.settings import settings
from src.instagram.collector import InstagramCollector
from src.instagram.date_filter import parse_timeframe
from src.instagram.engagement import sort_reels_by_viral_score
from src.instagram.rate_limiter import RateLimiter
from src.instagram.session_manager import InstagramSessionManager
from src.models.instagram import ReelItem
from src.reports.exporter import ReportExporter
from src.cli.views import (
    console,
    render_analysis_panel,
    render_banner,
    render_profile_analysis_panel,
    render_profile_card,
    render_reels_table,
    render_strategy_panel,
    render_transcripts_panel,
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
    timeframe: str = typer.Option(
        "all",
        "--timeframe",
        "-t",
        help="Filtrar Reels por período: '1w' (1 semana), '1m' (1 mês), '3m' (3 meses), '1y' (1 ano) ou dias como '7d'.",
    ),
    top_transcribe: int = typer.Option(
        3,
        "--top-transcribe",
        "-n",
        help="Quantidade dos Reels mais virais do nicho para baixar e transcrever com Whisper.",
    ),
    whisper_model: str = typer.Option(
        "base", "--whisper-model", "-w", help="Modelo Whisper: 'base', 'tiny' ou 'small'."
    ),
    language: str = typer.Option(
        "pt",
        "--language",
        "--lang",
        help="Idioma para transcrição do Whisper: 'pt' (padrão, português brasileiro), 'en', 'es', etc., ou 'auto' para detecção automática.",
    ),
    no_analysis: bool = typer.Option(False, "--no-analysis", help="Pula a análise qualitativa final do Gemini."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Exibe logs detalhados de depuração."),
) -> None:
    """Pesquisa Reels em qualquer nicho, orquestrado pela IA do Gemini."""
    setup_logging(level=logging.DEBUG if verbose else logging.INFO)
    render_banner()

    # Validação do período de tempo
    try:
        min_taken_at, timeframe_desc = parse_timeframe(timeframe)
    except ValueError as err:
        console.print(f"[bold red]Erro no parâmetro de período:[/bold red] {err}")
        raise typer.Exit(code=1)

    if min_taken_at:
        console.print(f"[bold cyan]Filtro de Período Ativo:[/bold cyan] [bold green]{timeframe_desc}[/bold green]\n")

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
    with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
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
                with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                    if term_type == "keyword":
                        progress.add_task(description=f"Pesquisando Reels por busca textual: '{term_val}'...", total=None)
                        reels_found = collector.search_reels_by_keyword(
                            term_val, amount=min(15, needed), min_taken_at=min_taken_at
                        )
                        label = f"busca:'{term_val}'"
                    else:
                        progress.add_task(description=f"Pesquisando Reels na hashtag #{term_val}...", total=None)
                        reels_found = collector.search_reels_by_hashtag(
                            term_val, amount=min(15, needed), min_taken_at=min_taken_at
                        )
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
        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
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

    # 7. Download e Transcrição com Whisper dos Top N Reels do Nicho
    if top_transcribe > 0:
        console.print(f"\n[bold cyan]Baixando e transcrevendo os {min(top_transcribe, len(ranked_reels))} Reels mais virais do nicho via Whisper ({language.upper()})...[/bold cyan]")
        audio_mgr = AudioTranscriptionManager(
            client=client,
            whisper_model=whisper_model,
            language=language,
        )

        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task(description="Iniciando processamento de áudio...", total=None)

            def update_progress_msg(msg: str):
                progress.update(task, description=msg)

            ranked_reels = audio_mgr.process_top_reels(
                ranked_reels, top_n=top_transcribe, status_callback=update_progress_msg
            )

        console.print("\n")
        render_transcripts_panel(ranked_reels)

    # 8. Engenharia Reversa com Gemini (Top 10)
    analysis = None
    if not no_analysis and len(ranked_reels) > 0:
        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task(description="Gemini decodificando os ganchos e estratégias dos Top Reels...", total=None)
            try:
                analysis = analyzer.analyze_top_reels(ranked_reels[:10], niche_topic=query)
            except Exception as exc:
                console.print(f"[yellow]Aviso: Não foi possível gerar a análise qualitativa: {exc}[/yellow]")

        if analysis:
            console.print("\n")
            render_analysis_panel(analysis)

    # 9. Exportação dos Relatórios
    paths = exporter.export_all(
        query=query,
        strategy=strategy,
        reels=ranked_reels,
        analysis=analysis,
        timeframe_desc=timeframe_desc,
    )
    console.print("\n[bold green]Relatórios gerados com sucesso:[/bold green]")
    console.print(f"  [cyan]Markdown:[/cyan] {paths['markdown']}")
    console.print(f"  [cyan]Planilha CSV:[/cyan] {paths['csv']}")
    console.print(f"  [cyan]JSON Estruturado:[/cyan] {paths['json']}")
    console.print("\n[dim]Abra o arquivo Markdown para visualizar todos os links clicáveis dos Reels.[/dim]\n")


@app.command()
def profile(
    username: str = typer.Argument(
        None, help="Nome de usuário do perfil no Instagram (ex: lucureau ou @lucureau)."
    ),
    username_opt: str = typer.Option(
        None, "--username", "-u", help="Nome de usuário alternativo via flag -u."
    ),
    limit: int = typer.Option(
        30, "--limit", "-l", help="Quantidade de Reels recentes do perfil a analisar."
    ),
    timeframe: str = typer.Option(
        "all", "--timeframe", "-t", help="Filtrar por período: '1w', '1m', '3m', '1y' ou 'all'."
    ),
    top_transcribe: int = typer.Option(
        3, "--top-transcribe", "-n", help="Quantidade dos Reels mais virais para baixar e transcrever com Whisper."
    ),
    whisper_model: str = typer.Option(
        "base", "--whisper-model", "-w", help="Modelo Whisper: 'base', 'tiny' ou 'small'."
    ),
    language: str = typer.Option(
        "pt",
        "--language",
        "--lang",
        help="Idioma para transcrição do Whisper: 'pt' (padrão, português brasileiro), 'en', 'es', etc., ou 'auto' para detecção automática.",
    ),
    no_analysis: bool = typer.Option(
        False, "--no-analysis", help="Pula a geração do diagnóstico qualitativo pelo Gemini."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Exibe logs detalhados de depuração."
    ),
) -> None:
    """Audita um perfil do Instagram, ranqueia Reels, transcreve com Whisper e decodifica roteiros com Gemini."""
    setup_logging(level=logging.DEBUG if verbose else logging.INFO)
    render_banner()

    target_username = username_opt or username
    if not target_username or target_username.startswith("-"):
        console.print(
            "\n[bold red]Erro de sintaxe:[/bold red] Nome de usuário não informado ou corrompido pelo terminal.\n"
            "[bold yellow]Dica para Windows / PowerShell:[/bold yellow]\n"
            "No PowerShell, o caractere '@' sem aspas é interpretado como variável/splat. Para rodar sem erro:\n"
            "  ✓ [bold green]python -m src.main profile lucureau -n 3[/bold green] (recomendado, sem arroba)\n"
            "  ✓ [bold green]python -m src.main profile \"@lucureau\" -n 3[/bold green] (com aspas duplas)\n"
            "  ✓ [bold green]python -m src.main profile -u lucureau -n 3[/bold green]\n"
        )
        raise typer.Exit(code=1)

    # Validação do período de tempo
    try:
        min_taken_at, timeframe_desc = parse_timeframe(timeframe)
    except ValueError as err:
        console.print(f"[bold red]Erro no parâmetro de período:[/bold red] {err}")
        raise typer.Exit(code=1)

    if min_taken_at:
        console.print(f"[bold cyan]Filtro de Período Ativo:[/bold cyan] [bold green]{timeframe_desc}[/bold green]\n")

    # Validação de credenciais
    if not settings.gemini_api_key and not no_analysis:
        console.print(
            "[bold red]Erro:[/bold red] Preencha `GEMINI_API_KEY` no seu arquivo .env com a chave do Google AI Studio."
        )
        raise typer.Exit(code=1)

    if not settings.instagram_sessionid and (not settings.instagram_username or not settings.instagram_password):
        console.print(
            "[bold red]Erro:[/bold red] Configure `INSTAGRAM_SESSIONID` ou `INSTAGRAM_USERNAME` e `INSTAGRAM_PASSWORD` no arquivo .env."
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

    collector = InstagramCollector(client=client)
    exporter = ReportExporter(output_dir=settings.outputs_dir)

    # 2. Obtenção dos dados cadastrais do perfil
    with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task(description=f"Consultando dados do perfil @{target_username.lstrip('@')}...", total=None)
        try:
            profile_data = collector.get_user_profile(target_username)
        except Exception as exc:
            console.print(f"[bold red]Erro ao buscar perfil:[/bold red] {exc}")
            raise typer.Exit(code=1)

    render_profile_card(profile_data)

    # 3. Coleta de Reels do perfil
    with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task(description=f"Coletando Reels de @{profile_data.username}...", total=None)
        try:
            reels = collector.get_user_reels(
                user_id=profile_data.pk, amount=limit, min_taken_at=min_taken_at
            )
        except (LoginRequired, ClientUnauthorizedError):
            console.print("\n[bold red]Sessão Expirada:[/bold red] A sessão foi invalidada pelo Instagram.")
            raise typer.Exit(code=1)

    if not reels:
        console.print("[bold yellow]Nenhum Reel encontrado para este perfil dentro do período selecionado.[/bold yellow]")
        raise typer.Exit(code=0)

    # 4. Ordenação decrescente por Viral Score
    ranked_reels = sort_reels_by_viral_score(reels)

    console.print("\n")
    render_reels_table(ranked_reels, limit=min(len(ranked_reels), 15))

    # 5. Download e Transcrição com Whisper dos Top N Reels
    if top_transcribe > 0:
        console.print(f"\n[bold cyan]Baixando e transcrevendo os {min(top_transcribe, len(ranked_reels))} Reels mais virais via Whisper ({language.upper()})...[/bold cyan]")
        audio_mgr = AudioTranscriptionManager(
            client=client,
            whisper_model=whisper_model,
            language=language,
        )

        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task(description="Iniciando processamento de áudio...", total=None)

            def update_progress_msg(msg: str):
                progress.update(task, description=msg)

            ranked_reels = audio_mgr.process_top_reels(
                ranked_reels, top_n=top_transcribe, status_callback=update_progress_msg
            )

        console.print("\n")
        render_transcripts_panel(ranked_reels)

    # 6. Análise Estratégica Completa com o Gemini
    profile_analysis = None
    if not no_analysis:
        console.print("\n[bold cyan]Gerando diagnóstico estratégico e decodificação de roteiros com Gemini...[/bold cyan]")
        gemini_client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
        analyzer = ProfileAnalyzer(gemini_client=gemini_client)

        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task(description="Gemini analisando bio, posicionamento e transcrições...", total=None)
            try:
                profile_analysis = analyzer.analyze_profile(profile=profile_data, reels=ranked_reels)
            except Exception as exc:
                console.print(f"[yellow]Aviso: Não foi possível gerar a análise da IA: {exc}[/yellow]")

        if profile_analysis:
            console.print("\n")
            render_profile_analysis_panel(profile_analysis)

    # 7. Exportação dos Relatórios
    paths = exporter.export_profile_all(
        profile=profile_data,
        reels=ranked_reels,
        analysis=profile_analysis,
        timeframe_desc=timeframe_desc,
    )

    console.print("\n[bold green]Relatórios de Auditoria gerados com sucesso:[/bold green]")
    console.print(f"  [cyan]Markdown Executivo:[/cyan] {paths['markdown']}")
    console.print(f"  [cyan]Planilha CSV:[/cyan] {paths['csv']}")
    console.print(f"  [cyan]JSON Estruturado:[/cyan] {paths['json']}")
    console.print("\n[dim]Abra o arquivo Markdown para visualizar todos os roteiros transcritos e links dos Reels.[/dim]\n")


@app.command(name="ui")
def ui(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Endereço de IP do servidor web local."),
    port: int = typer.Option(8000, "--port", "-p", help="Porta TCP do servidor web."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Não abre automaticamente o navegador ao iniciar."),
) -> None:
    """Inicia a interface visual web (Dashboard) para pesquisa, transcrição e relatórios."""
    import webbrowser
    from src.web.server import run_server

    render_banner()
    url = f"http://{host}:{port}"
    console.print(f"\n[bold green]Iniciando Interface Visual Web:[/bold green] [underline cyan]{url}[/underline cyan]")
    console.print("[dim]Pressione CTRL+C no terminal para encerrar o servidor web.[/dim]\n")

    if not no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        run_server(host=host, port=port)
    except KeyboardInterrupt:
        console.print("\n[yellow]Servidor web encerrado pelo usuário.[/yellow]")


@app.command(name="web")
def web_alias(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Endereço de IP do servidor web local."),
    port: int = typer.Option(8000, "--port", "-p", help="Porta TCP do servidor web."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Não abre automaticamente o navegador ao iniciar."),
) -> None:
    """Alias para o comando 'ui': inicia o painel web visual no navegador."""
    ui(host=host, port=port, no_browser=no_browser)

