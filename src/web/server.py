"""Servidor web assíncrono para interface visual da aplicação."""
import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
from aiohttp import web
from src.agent.gemini_client import GeminiClient
from src.agent.profile_analyzer import ProfileAnalyzer
from src.agent.search_planner import SearchPlanner
from src.agent.viral_analyzer import ViralAnalyzer
from src.audio.manager import AudioTranscriptionManager
from src.config.settings import settings
from src.instagram.collector import InstagramCollector
from src.instagram.date_filter import parse_timeframe
from src.instagram.engagement import sort_reels_by_viral_score
from src.instagram.session_manager import InstagramSessionManager
from src.models.instagram import ReelItem
from src.reports.exporter import ReportExporter

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class AppServer:
    """Servidor da interface web que expõe as funcionalidades da aplicação via REST."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000):
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self) -> None:
        # Página principal (SPA)
        self.app.router.add_get("/", self.handle_index)

        # APIs de Status e Credenciais
        self.app.router.add_get("/api/status", self.handle_status)

        # APIs de Operação (Pesquisa de Nicho e Auditoria de Perfil)
        self.app.router.add_post("/api/search", self.handle_search)
        self.app.router.add_post("/api/profile", self.handle_profile)

        # APIs de Relatórios e Download
        self.app.router.add_get("/api/reports", self.handle_list_reports)
        self.app.router.add_get("/api/reports/download/{filename}", self.handle_download_report)

        # Arquivos estáticos
        if STATIC_DIR.exists():
            self.app.router.add_static("/static/", path=STATIC_DIR, name="static")

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve o front-end HTML da Single Page Application."""
        index_file = STATIC_DIR / "index.html"
        if not index_file.exists():
            return web.Response(text="Front-end não encontrado.", status=404)
        return web.FileResponse(index_file)

    async def handle_status(self, request: web.Request) -> web.Response:
        """Retorna o status atual das conexões (Instagram e Gemini)."""
        session_file = settings.instagram_session_dir / f"{settings.instagram_username or 'instagram'}.session.json"
        is_instagram_connected = session_file.exists() or bool(settings.instagram_sessionid) or (
            bool(settings.instagram_username) and bool(settings.instagram_password)
        )
        data = {
            "gemini_ready": bool(settings.gemini_api_key),
            "gemini_model": settings.gemini_model,
            "instagram_ready": is_instagram_connected,
            "instagram_username": settings.instagram_username,
            "has_session_file": session_file.exists(),
        }
        return web.json_response(data)

    async def handle_search(self, request: web.Request) -> web.Response:
        """Executa a pesquisa de nicho em background e retorna os resultados estruturados."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Corpo da requisição JSON inválido."}, status=400)

        query = body.get("query", "").strip()
        if not query:
            return web.json_response({"error": "O campo 'query' é obrigatório."}, status=400)

        limit = int(body.get("limit", 20))
        rounds = int(body.get("rounds", 2))
        timeframe = str(body.get("timeframe", "all"))
        top_transcribe = int(body.get("top_transcribe", 3))
        whisper_model = str(body.get("whisper_model", "base"))
        language = str(body.get("language", "pt"))
        no_analysis = bool(body.get("no_analysis", False))

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                self._execute_search_sync,
                query,
                limit,
                rounds,
                timeframe,
                top_transcribe,
                whisper_model,
                language,
                no_analysis,
            )
            return web.json_response(result)
        except Exception as exc:
            logger.exception("Erro durante a pesquisa de nicho:")
            return web.json_response({"error": str(exc)}, status=500)

    def _execute_search_sync(
        self,
        query: str,
        limit: int,
        rounds: int,
        timeframe: str,
        top_transcribe: int,
        whisper_model: str,
        language: str,
        no_analysis: bool,
    ) -> dict:
        """Lógica síncrona de execução da pesquisa de nicho."""
        min_taken_at, timeframe_desc = parse_timeframe(timeframe)

        # 1. Autenticação no Instagram
        session_mgr = InstagramSessionManager(
            username=settings.instagram_username,
            password=settings.instagram_password,
            session_dir=settings.instagram_session_dir,
            sessionid=settings.instagram_sessionid,
            two_factor_seed=settings.instagram_2fa_seed,
            proxy=settings.instagram_proxy,
        )
        client = session_mgr.get_authenticated_client()
        collector = InstagramCollector(client=client)
        exporter = ReportExporter(output_dir=settings.outputs_dir)

        # 2. Agente Gemini Planejador
        gemini_client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
        planner = SearchPlanner(gemini_client=gemini_client)
        strategy = planner.plan_search(query)

        # 3. Coleta Híbrida
        all_reels: list[ReelItem] = []
        explored_terms: list[str] = []

        initial_search_items = [{"type": "keyword", "value": query}]
        for kw in strategy.search_keywords:
            initial_search_items.append({"type": "keyword", "value": kw})
        for tag in strategy.primary_hashtags + strategy.long_tail_hashtags:
            initial_search_items.append({"type": "hashtag", "value": tag})

        current_queue = initial_search_items

        for current_round in range(1, rounds + 1):
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

                if term_type == "keyword":
                    reels_found = collector.search_reels_by_keyword(
                        term_val, amount=min(15, needed), min_taken_at=min_taken_at
                    )
                else:
                    reels_found = collector.search_reels_by_hashtag(
                        term_val, amount=min(15, needed), min_taken_at=min_taken_at
                    )
                all_reels.extend(reels_found)

            if len(all_reels) >= limit or current_round == rounds:
                break

            evaluation = planner.evaluate_and_refine(
                current_reels=all_reels,
                target_count=limit,
                explored_terms=[t.split(":", 1)[-1] for t in explored_terms],
                original_query=query,
            )
            if not evaluation.should_continue or not evaluation.new_terms_to_try:
                break

            current_queue = []
            for new_term in evaluation.new_terms_to_try:
                if new_term.startswith("#"):
                    current_queue.append({"type": "hashtag", "value": new_term.lstrip("#")})
                else:
                    current_queue.append({"type": "keyword", "value": new_term})

        ranked_reels = sort_reels_by_viral_score(all_reels)

        # 4. Transcrição com Whisper dos Top N
        if top_transcribe > 0 and ranked_reels:
            audio_mgr = AudioTranscriptionManager(
                client=client, whisper_model=whisper_model, language=language
            )
            ranked_reels = audio_mgr.process_top_reels(ranked_reels, top_n=top_transcribe)

        # 5. Análise do Gemini
        analysis = None
        if not no_analysis and ranked_reels:
            analyzer = ViralAnalyzer(gemini_client=gemini_client)
            analysis = analyzer.analyze_top_reels(ranked_reels[:10], niche_topic=query)

        # 6. Exportação dos relatórios
        paths = exporter.export_all(
            query=query,
            strategy=strategy,
            reels=ranked_reels,
            analysis=analysis,
            timeframe_desc=timeframe_desc,
        )

        return {
            "success": True,
            "query": query,
            "timeframe": timeframe_desc,
            "strategy": strategy.model_dump(),
            "analysis": analysis.model_dump() if analysis else None,
            "total_reels": len(ranked_reels),
            "reels": [r.model_dump(mode="json") for r in ranked_reels],
            "reports": {k: p.name for k, p in paths.items()},
        }

    async def handle_profile(self, request: web.Request) -> web.Response:
        """Executa a auditoria de perfil em background e retorna os resultados estruturados."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Corpo da requisição JSON inválido."}, status=400)

        username = body.get("username", "").strip()
        if not username:
            return web.json_response({"error": "O campo 'username' é obrigatório."}, status=400)

        limit = int(body.get("limit", 30))
        timeframe = str(body.get("timeframe", "all"))
        top_transcribe = int(body.get("top_transcribe", 3))
        whisper_model = str(body.get("whisper_model", "base"))
        language = str(body.get("language", "pt"))
        no_analysis = bool(body.get("no_analysis", False))

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                self._execute_profile_sync,
                username,
                limit,
                timeframe,
                top_transcribe,
                whisper_model,
                language,
                no_analysis,
            )
            return web.json_response(result)
        except Exception as exc:
            logger.exception("Erro durante a auditoria de perfil:")
            return web.json_response({"error": str(exc)}, status=500)

    def _execute_profile_sync(
        self,
        username: str,
        limit: int,
        timeframe: str,
        top_transcribe: int,
        whisper_model: str,
        language: str,
        no_analysis: bool,
    ) -> dict:
        """Lógica síncrona de execução da auditoria de perfil."""
        min_taken_at, timeframe_desc = parse_timeframe(timeframe)

        session_mgr = InstagramSessionManager(
            username=settings.instagram_username,
            password=settings.instagram_password,
            session_dir=settings.instagram_session_dir,
            sessionid=settings.instagram_sessionid,
            two_factor_seed=settings.instagram_2fa_seed,
            proxy=settings.instagram_proxy,
        )
        client = session_mgr.get_authenticated_client()
        collector = InstagramCollector(client=client)
        exporter = ReportExporter(output_dir=settings.outputs_dir)

        # 1. Obtenção do perfil
        profile = collector.get_user_profile(username)

        # 2. Coleta de Reels do perfil
        reels = collector.get_user_reels(user_id=profile.pk, amount=limit, min_taken_at=min_taken_at)
        ranked_reels = sort_reels_by_viral_score(reels)

        # 3. Download e Transcrição com Whisper
        if top_transcribe > 0 and ranked_reels:
            audio_mgr = AudioTranscriptionManager(
                client=client, whisper_model=whisper_model, language=language
            )
            ranked_reels = audio_mgr.process_top_reels(ranked_reels, top_n=top_transcribe)

        # 4. Análise com Gemini
        analysis = None
        if not no_analysis and ranked_reels:
            gemini_client = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
            analyzer = ProfileAnalyzer(gemini_client=gemini_client)
            analysis = analyzer.analyze_profile(profile=profile, reels=ranked_reels)

        # 5. Exportação
        paths = exporter.export_profile_all(
            profile=profile,
            reels=ranked_reels,
            analysis=analysis,
            timeframe_desc=timeframe_desc,
        )

        return {
            "success": True,
            "profile": profile.model_dump(),
            "timeframe": timeframe_desc,
            "analysis": analysis.model_dump() if analysis else None,
            "total_reels": len(ranked_reels),
            "reels": [r.model_dump(mode="json") for r in ranked_reels],
            "reports": {k: p.name for k, p in paths.items()},
        }

    async def handle_list_reports(self, request: web.Request) -> web.Response:
        """Lista todos os relatórios disponíveis no diretório outputs/."""
        reports_dir = settings.outputs_dir
        if not reports_dir.exists():
            return web.json_response([])

        items = []
        for f in sorted(reports_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix in (".md", ".csv", ".json"):
                items.append({
                    "filename": f.name,
                    "extension": f.suffix.lstrip("."),
                    "size_bytes": f.stat().st_size,
                    "modified_at": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
                })
        return web.json_response(items)

    async def handle_download_report(self, request: web.Request) -> web.Response:
        """Realiza o download de um arquivo de relatório pelo nome."""
        filename = request.match_info.get("filename", "")
        # Sanitização de segurança para impedir path traversal
        clean_name = Path(filename).name
        file_path = settings.outputs_dir / clean_name

        if not file_path.exists() or not file_path.is_file():
            return web.Response(text="Arquivo não encontrado.", status=404)

        return web.FileResponse(
            file_path,
            headers={
                "Content-Disposition": f'attachment; filename="{clean_name}"',
            },
        )


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Inicia a aplicação aiohttp em loop de eventos."""
    server = AppServer(host=host, port=port)
    web.run_app(server.app, host=host, port=port)
