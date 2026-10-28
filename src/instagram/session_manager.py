"""Gerenciamento de autenticação, persistência de sessão e 2FA do Instagram."""
import base64
import json
import logging
import re
from pathlib import Path
from instagrapi import Client
from instagrapi.exceptions import (
    BadPassword,
    ChallengeRequired,
    ClientUnauthorizedError,
    LoginRequired,
    TwoFactorRequired,
)

logger = logging.getLogger(__name__)

DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)
WEB_APP_ID = "936619743392459"


class InstagramSessionManager:
    """Gerencia autenticação segura e reutilização de sessões do instagrapi."""

    def __init__(
        self,
        username: str = "",
        password: str = "",
        session_dir: Path = Path("sessions"),
        sessionid: str | None = None,
        two_factor_seed: str | None = None,
        proxy: str | None = None,
    ):
        self.username = username.strip() if username else ""
        self.password = password.strip() if password else ""
        self.session_dir = Path(session_dir)
        self.sessionid = sessionid.strip() if sessionid else None
        self.two_factor_seed = two_factor_seed
        self.proxy = proxy

        clean_name = re.sub(r"[^\w.-]", "_", self.username) if self.username else "instagram"
        self.session_file = self.session_dir / f"{clean_name}.session.json"
        self.client = Client()

        # Vincula o handler interativo de verificação de segurança (Email/SMS Challenge)
        self.client.challenge_code_handler = self._challenge_code_handler

        if self.proxy:
            self.client.set_proxy(self.proxy)

    def get_authenticated_client(self) -> Client:
        """Retorna uma instância de Client autenticada e validada."""
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # 1. Tenta carregar e validar sessão existente em disco
        if self.session_file.exists():
            logger.info(f"Carregando sessão existente de {self.session_file}...")
            try:
                self.client.load_settings(self.session_file)
                self.client.get_timeline_feed()
                logger.info("Sessão salva validada com sucesso!")
                return self.client
            except (LoginRequired, ClientUnauthorizedError):
                logger.warning("Sessão salva expirada no Instagram. Removendo arquivo local...")
                self.session_file.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning(f"Erro ao verificar sessão salva ({exc}). Removendo cache...")
                self.session_file.unlink(missing_ok=True)

        # 2. Se o usuário forneceu INSTAGRAM_SESSIONID, tenta autenticar por cookies
        if self.sessionid:
            logger.info("Tentando autenticação via cookies configurados no INSTAGRAM_SESSIONID...")
            try:
                self._apply_session_cookies(self.sessionid)
                self.client.get_timeline_feed()
                self.client.dump_settings(self.session_file)
                logger.info(f"Sessão validada com sucesso e salva em {self.session_file}")
                return self.client
            except (LoginRequired, ClientUnauthorizedError) as exc:
                logger.warning(f"INSTAGRAM_SESSIONID inválido ou expirado ({exc}).")
                # Se temos usuário e senha, tenta o login nativo com tratamento de desafio
                if self.username and self.password:
                    logger.info("Prosseguindo para login nativo com usuário e senha...")
                    return self._login_fresh()
                raise RuntimeError(
                    "O cookie `INSTAGRAM_SESSIONID` configurado no arquivo .env expirou ou é inválido.\n"
                    "Configure seu INSTAGRAM_USERNAME e INSTAGRAM_PASSWORD no .env para login direto."
                ) from exc
            except Exception as exc:
                logger.warning(f"Aviso na validação inicial do feed: {exc}. Salvando sessão e prosseguindo...")
                self.client.dump_settings(self.session_file)
                return self.client

        # 3. Tenta login por usuário e senha
        return self._login_fresh()

    def _apply_session_cookies(self, cookie_input: str) -> None:
        """Injeta cookies web sem cabeçalhos conflitantes de Android para proteger a sessão."""
        clean_input = cookie_input.strip().strip("'\"")

        cookies_dict = {}
        if ";" in clean_input or "=" in clean_input:
            for item in clean_input.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookies_dict[k.strip()] = v.strip()
        else:
            cookies_dict["sessionid"] = clean_input

        sessionid = cookies_dict.get("sessionid", clean_input)

        user_id = cookies_dict.get("ds_user_id")
        if not user_id:
            user_match = re.search(r"^\d+", sessionid)
            user_id = user_match.group() if user_match else "0"
            cookies_dict["ds_user_id"] = str(user_id)

        auth_data = {
            "ds_user_id": str(user_id),
            "sessionid": sessionid,
            "should_use_header_over_cookies": True,
        }
        b64part = base64.b64encode(json.dumps(auth_data).encode()).decode()

        self.client.settings["cookies"] = cookies_dict
        self.client.settings["authorization_data"] = auth_data
        self.client.init()

        for name, value in cookies_dict.items():
            self.client.private.cookies.set(name, value, domain=".instagram.com")
            self.client.public.cookies.set(name, value, domain=".instagram.com")

        self.client.private.headers.update({"Authorization": f"Bearer IGT:2:{b64part}"})
        if self.username:
            self.client.username = self.username

        self._apply_web_anti_invalidation_headers()

    def _apply_web_anti_invalidation_headers(self) -> None:
        """Substitui o User-Agent e remove cabeçalhos de Android conflitantes."""
        self.client.set_user_agent(DESKTOP_USER_AGENT)

        android_conflict_headers = [
            "X-IG-Android-ID",
            "X-Bloks-Version-Id",
            "X-Pigeon-Session-Id",
            "X-FB-HTTP-Engine",
            "X-IG-Capabilities",
            "X-Tigon-Is-Retry",
            "X-IG-Device-ID",
            "X-IG-Family-Device-ID",
        ]
        for h in android_conflict_headers:
            self.client.private.headers.pop(h, None)

        self.client.private.headers.update({
            "User-Agent": DESKTOP_USER_AGENT,
            "X-IG-App-ID": WEB_APP_ID,
            "Referer": "https://www.instagram.com/",
        })
        self.client.public.headers.update({
            "User-Agent": DESKTOP_USER_AGENT,
            "X-IG-App-ID": WEB_APP_ID,
            "Referer": "https://www.instagram.com/",
        })

    def _login_fresh(self) -> Client:
        """Executa login com usuário e senha com suporte a verificação de código por e-mail/SMS."""
        if not self.username or not self.password:
            raise ValueError(
                "Credenciais incompletas. Preencha INSTAGRAM_USERNAME e INSTAGRAM_PASSWORD no .env."
            )

        if "@" in self.username:
            print("\n" + "!" * 70)
            print("[AVISO]: Você configurou um endereço de e-mail no INSTAGRAM_USERNAME:")
            print(f"  -> '{self.username}'")
            print("O Instagram frequentemente rejeita e-mail em logins de API.")
            print("Recomendado usar o seu nome de usuário (ex: 'meu_perfil', sem @).")
            print("!" * 70 + "\n")

        clean_user = self.username.lstrip("@").strip()
        logger.info(f"Iniciando login nativo com usuário e senha para @{clean_user}...")

        # Assegura que o challenge_code_handler está ativo antes de logar
        self.client.challenge_code_handler = self._challenge_code_handler

        try:
            self.client.login(clean_user, self.password)
        except TwoFactorRequired:
            code = self._get_two_factor_code()
            logger.info("Enviando código 2FA...")
            self.client.two_factor_login(code)
        except ChallengeRequired as err:
            logger.info("Tentando resolver desafio de segurança automaticamente...")
            try:
                code = self._challenge_code_handler(clean_user, choice="email")
                self.client.challenge_resolve(code)
            except Exception as chal_err:
                raise RuntimeError(
                    f"Falha ao validar código de segurança do Instagram: {chal_err}"
                ) from err
        except BadPassword as err:
            logger.error("Usuário ou senha do Instagram incorretos.")
            raise ValueError("Credenciais do Instagram inválidas. Verifique usuário e senha no .env.") from err
        except Exception as err:
            err_msg = str(err).lower()
            if "upgrade your app" in err_msg or "out of date" in err_msg or "needs_upgrade" in err_msg:
                raise RuntimeError(
                    "O Instagram exigiu verificação de segurança ou rejeitou o login direto.\n"
                    "DICA: Verifique se o INSTAGRAM_USERNAME no .env é o nome de usuário (ex: adventistas.itaoca),\n"
                    "e execute: python -m src.main login para digitar o código de confirmação enviado ao seu e-mail."
                ) from err
            raise

        self.client.dump_settings(self.session_file)
        logger.info(f"Nova sessão salva com sucesso em {self.session_file}")
        return self.client

    def _challenge_code_handler(self, username: str, choice=None) -> str:
        """Handler interativo para códigos de verificação de segurança enviados por e-mail ou SMS."""
        choice_str = "E-mail" if "email" in str(choice).lower() else "SMS" if "sms" in str(choice).lower() else "E-mail ou SMS"
        print("\n" + "=" * 70)
        print(f"[!] Verificação de Segurança do Instagram (Código via {choice_str})")
        print(f"O Instagram enviou um código de confirmação de 6 dígitos para o seu {choice_str}.")
        print("Por favor, abra sua caixa de entrada (ou SMS) e verifique o código recebido.")
        print("=" * 70)

        code = ""
        while not code:
            code = input(f"\nDigite o código de 6 dígitos recebido por {choice_str}: ").strip()
            if not code or not code.isdigit():
                print("Por favor, digite apenas os dígitos numéricos do código.")
                code = ""
        return code

    def _get_two_factor_code(self) -> str:
        """Obtém o código 2FA via chave TOTP do .env ou solicita entrada do usuário."""
        if self.two_factor_seed:
            try:
                import pyotp
                totp = pyotp.TOTP(self.two_factor_seed.replace(" ", ""))
                code = totp.now()
                logger.info("Código 2FA gerado automaticamente via chave TOTP.")
                return code
            except Exception as err:
                logger.warning(f"Falha ao gerar código TOTP automático: {err}. Solicitando manualmente...")

        print("\n" + "=" * 50)
        print("Autenticação de Dois Fatores (2FA) necessária para o Instagram.")
        code = input("Digite o código de 6 dígitos gerado no seu app autenticador: ").strip()
        print("=" * 50 + "\n")
        return code
