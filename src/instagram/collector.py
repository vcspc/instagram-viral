"""Coletor de publicações focado em Reels com múltiplos fallbacks, busca textual e análise de perfis."""
import logging
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import (
    ClientUnauthorizedError,
    LoginRequired,
    RateLimitError,
    UserNotFound,
)
from instagrapi.extractors import extract_media_v1
from src.instagram.date_filter import is_within_timeframe
from src.instagram.engagement import calculate_metrics
from src.instagram.rate_limiter import RateLimiter
from src.models.instagram import ReelItem, UserProfile

logger = logging.getLogger(__name__)


class InstagramCollector:
    """Coleta e filtra Reels a partir de termos de busca, hashtags e perfis no Instagram."""

    def __init__(self, client: Client, rate_limiter: RateLimiter | None = None):
        self.client = client
        self.rate_limiter = rate_limiter or RateLimiter()
        self._seen_pks: set[str] = set()

    def get_user_profile(self, username: str) -> UserProfile:
        """Obtém os dados cadastrais e estatísticas públicas de um perfil do Instagram."""
        clean_user = username.lstrip("@").strip()
        if not clean_user:
            raise ValueError("O nome de usuário não pode ser vazio.")

        logger.info(f"Buscando dados do perfil @{clean_user} no Instagram...")
        self.rate_limiter.wait()

        try:
            user = self.client.user_info_by_username(clean_user)
            self.rate_limiter.reset_errors()
        except UserNotFound as err:
            raise ValueError(f"O perfil @{clean_user} não foi encontrado no Instagram.") from err
        except (LoginRequired, ClientUnauthorizedError):
            logger.error("Sessão do Instagram expirada ao buscar perfil.")
            raise
        except Exception as exc:
            logger.error(f"Erro ao consultar perfil @{clean_user}: {exc}")
            raise

        return UserProfile(
            pk=str(getattr(user, "pk", "")),
            username=getattr(user, "username", clean_user),
            full_name=getattr(user, "full_name", "") or "",
            biography=getattr(user, "biography", "") or "",
            follower_count=getattr(user, "follower_count", 0) or 0,
            following_count=getattr(user, "following_count", 0) or 0,
            media_count=getattr(user, "media_count", 0) or 0,
            is_verified=bool(getattr(user, "is_verified", False)),
            is_business=bool(getattr(user, "is_business", False)),
            external_url=getattr(user, "external_url", "") or "",
            category=getattr(user, "category_name", "") or "",
            profile_pic_url=str(getattr(user, "profile_pic_url", "") or ""),
        )

    def get_user_reels(
        self, user_id: str, amount: int = 30, min_taken_at: datetime | None = None
    ) -> list[ReelItem]:
        """Obtém os Reels mais recentes de um perfil com suporte a paginação e filtro de período."""
        logger.info(f"Buscando até {amount} Reels do criador ID {user_id}...")
        self.rate_limiter.wait()

        results: list[ReelItem] = []
        medias = []

        try:
            # 1. Tenta método nativo de clips/reels
            medias = self.client.user_clips_v1(user_id=user_id, amount=amount)
            self.rate_limiter.reset_errors()
        except (LoginRequired, ClientUnauthorizedError):
            logger.error("Sessão do Instagram expirada ao buscar Reels do perfil.")
            raise
        except Exception as exc:
            logger.warning(f"user_clips_v1 falhou para {user_id}: {exc}. Recorrendo a user_medias_v1...")
            try:
                all_medias = self.client.user_medias_v1(user_id=user_id, amount=amount)
                medias = [m for m in all_medias if self._is_reel_or_video(m)]
            except (LoginRequired, ClientUnauthorizedError):
                raise
            except Exception as e:
                logger.error(f"Falha ao obter mídias do usuário {user_id}: {e}")
                return []

        for media in medias:
            if not self._is_reel_or_video(media):
                continue

            if not is_within_timeframe(getattr(media, "taken_at", None), min_taken_at):
                continue

            pk = str(getattr(media, "pk", ""))
            if not pk or pk in self._seen_pks:
                continue

            self._seen_pks.add(pk)
            reel_item = self._parse_media_to_reel(media, source_term=f"perfil:{user_id}")
            results.append(reel_item)

        logger.info(f"Coletados {len(results)} Reels únicos do perfil.")
        return results

    def search_reels_by_keyword(
        self, keyword: str, amount: int = 20, min_taken_at: datetime | None = None
    ) -> list[ReelItem]:
        """Pesquisa Reels diretamente por termo ou palavra-chave na busca do Instagram."""
        clean_kw = keyword.strip()
        if not clean_kw:
            return []

        logger.info(f"Buscando Reels por palavra-chave: '{clean_kw}' (limite: {amount})...")
        self.rate_limiter.wait()

        results: list[ReelItem] = []
        medias = []

        # 1. Tenta media_search (endpoint nativo de busca de mídias do Instagram)
        try:
            medias = self.client.media_search(clean_kw, amount=amount)
            self.rate_limiter.reset_errors()
        except (LoginRequired, ClientUnauthorizedError):
            logger.error("Sessão do Instagram expirada durante media_search.")
            raise
        except RateLimitError:
            self.rate_limiter.handle_rate_limit()
            return []
        except Exception as err:
            logger.warning(f"Tentativa com media_search para '{clean_kw}' falhou: {err}")

        # 2. Se media_search retornar vazio, tenta fbsearch_reels_v2 diretamente
        if not medias:
            try:
                logger.info(f"Tentando endpoint SERP de Reels (fbsearch_reels_v2) para '{clean_kw}'...")
                resp = self.client.fbsearch_reels_v2(clean_kw)
                medias = self._extract_medias_from_serp(resp)
            except (LoginRequired, ClientUnauthorizedError):
                logger.error("Sessão do Instagram expirada durante fbsearch_reels_v2.")
                raise
            except Exception as err:
                logger.debug(f"fbsearch_reels_v2 falhou para '{clean_kw}': {err}")

        for media in medias:
            if not self._is_reel_or_video(media):
                continue

            if not is_within_timeframe(getattr(media, "taken_at", None), min_taken_at):
                continue

            pk = str(getattr(media, "pk", ""))
            if not pk or pk in self._seen_pks:
                continue

            self._seen_pks.add(pk)
            reel_item = self._parse_media_to_reel(media, source_term=f"busca:'{clean_kw}'")
            results.append(reel_item)

        logger.info(f"Encontrados {len(results)} Reels únicos pela palavra-chave '{clean_kw}'")
        return results

    def search_reels_by_hashtag(
        self, hashtag: str, amount: int = 20, min_taken_at: datetime | None = None
    ) -> list[ReelItem]:
        """Pesquisa Reels associados a uma hashtag com estratégia em cascata."""
        clean_tag = hashtag.lstrip("#").strip().lower()
        if not clean_tag:
            return []

        logger.info(f"Buscando Reels na hashtag #{clean_tag} (limite: {amount})...")
        self.rate_limiter.wait()

        results: list[ReelItem] = []
        medias = []

        # Estratégia 1: hashtag_medias_reels_v1 (específica para a aba 'clips' de Reels)
        try:
            medias = self.client.hashtag_medias_reels_v1(clean_tag, amount=amount)
            self.rate_limiter.reset_errors()
        except (LoginRequired, ClientUnauthorizedError):
            logger.error(f"Sessão do Instagram expirada ao buscar hashtag #{clean_tag}.")
            raise
        except RateLimitError:
            self.rate_limiter.handle_rate_limit()
            return []
        except Exception as err:
            logger.debug(f"hashtag_medias_reels_v1 falhou para #{clean_tag}: {err}")

        # Estratégia 2 (Fallback): hashtag_medias_recent_v1 (aba recentes)
        if not medias:
            try:
                logger.info(f"Recorrendo à aba recentes para #{clean_tag}...")
                medias = self.client.hashtag_medias_recent_v1(clean_tag, amount=amount)
            except (LoginRequired, ClientUnauthorizedError):
                logger.error(f"Sessão do Instagram expirada ao buscar hashtag #{clean_tag} (recent).")
                raise
            except Exception as err:
                logger.debug(f"hashtag_medias_recent_v1 falhou para #{clean_tag}: {err}")

        # Estratégia 3 (Fallback): hashtag_medias_top_v1 (aba top)
        if not medias:
            try:
                logger.info(f"Recorrendo à aba top para #{clean_tag}...")
                medias = self.client.hashtag_medias_top_v1(clean_tag, amount=amount)
            except Exception as err:
                logger.debug(f"hashtag_medias_top_v1 falhou para #{clean_tag}: {err}")

        # Estratégia 4 (Fallback): media_search textual com a hashtag
        if not medias:
            try:
                logger.info(f"Recorrendo à busca geral para #{clean_tag}...")
                medias = self.client.media_search(f"#{clean_tag}", amount=amount)
            except Exception as err:
                logger.debug(f"media_search com #{clean_tag} falhou: {err}")

        for media in medias:
            if not self._is_reel_or_video(media):
                continue

            if not is_within_timeframe(getattr(media, "taken_at", None), min_taken_at):
                continue

            pk = str(getattr(media, "pk", ""))
            if not pk or pk in self._seen_pks:
                continue

            self._seen_pks.add(pk)
            reel_item = self._parse_media_to_reel(media, source_term=f"#{clean_tag}")
            results.append(reel_item)

        logger.info(f"Encontrados {len(results)} Reels únicos na hashtag #{clean_tag}")
        return results

    def discover_related_tags(self, keyword: str) -> list[str]:
        """Pesquisa hashtags relacionadas a um termo textual."""
        clean_keyword = keyword.lstrip("#").strip()
        self.rate_limiter.wait()

        try:
            tags = self.client.search_tags(clean_keyword)
            return [t.name for t in tags if getattr(t, "name", None)]
        except Exception as err:
            logger.warning(f"Erro ao pesquisar tags para '{clean_keyword}': {err}")
            return []

    def _is_reel_or_video(self, media) -> bool:
        """Verifica de forma ampla se uma mídia é um Reel/Vídeo do Instagram."""
        if getattr(media, "media_type", None) == 2:
            return True

        product_type = getattr(media, "product_type", None)
        if product_type in ("clips", "igtv"):
            return True

        duration = getattr(media, "video_duration", 0.0)
        if duration and float(duration) > 0:
            return True

        return False

    def _extract_medias_from_serp(self, serp_dict: dict) -> list:
        """Extrai nós de mídia a partir da resposta bruta de busca SERP do Instagram."""
        medias = []
        if not isinstance(serp_dict, dict):
            return medias

        sections = serp_dict.get("sections") or serp_dict.get("media_grid", {}).get("sections") or []
        for section in sections:
            layout_content = section.get("layout_content") or {}
            one_by_two = layout_content.get("one_by_two_item") or {}
            clips = one_by_two.get("clips") or {}
            for item in clips.get("items") or []:
                node = item.get("media") if isinstance(item, dict) else None
                if node and isinstance(node, dict):
                    try:
                        medias.append(extract_media_v1(node))
                    except Exception:
                        pass
            for key in ("fill_items", "medias"):
                for item in layout_content.get(key) or []:
                    node = item.get("media") if isinstance(item, dict) else None
                    if node and isinstance(node, dict):
                        try:
                            medias.append(extract_media_v1(node))
                        except Exception:
                            pass

        return medias

    def _parse_media_to_reel(self, media, source_term: str) -> ReelItem:
        """Extrai os campos de interesse de uma mídia do instagrapi e calcula métricas."""
        code = getattr(media, "code", "")
        url = f"https://www.instagram.com/reel/{code}/" if code else ""
        caption = getattr(media, "caption_text", "") or ""
        duration = float(getattr(media, "video_duration", 0.0) or 0.0)
        taken_at = getattr(media, "taken_at", None)

        author_obj = getattr(media, "user", None)
        author_username = getattr(author_obj, "username", "") if author_obj else ""

        # Preserva URL direta de vídeo CDN
        video_url = getattr(media, "video_url", None)
        if not video_url and getattr(media, "video_versions", None):
            try:
                video_url = sorted(
                    media.video_versions,
                    key=lambda o: getattr(o, "height", 0) * getattr(o, "width", 0),
                )[-1].url
            except Exception:
                pass

        views = (
            getattr(media, "play_count", None)
            or getattr(media, "view_count", None)
            or getattr(media, "video_play_count", None)
            or 0
        )
        likes = getattr(media, "like_count", 0) or 0
        comments = getattr(media, "comment_count", 0) or 0

        if views == 0 and likes > 0:
            views = max(likes * 5, 1)

        metrics = calculate_metrics(views=views, likes=likes, comments=comments)

        return ReelItem(
            pk=str(getattr(media, "pk", "")),
            code=code,
            url=url,
            caption=caption,
            duration=duration,
            taken_at=taken_at,
            author_username=author_username,
            video_url=str(video_url) if video_url else None,
            metrics=metrics,
            source_term=source_term,
        )
