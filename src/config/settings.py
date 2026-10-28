"""Configurações da aplicação."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Instagram
    instagram_username: str = ""
    instagram_password: str = ""
    instagram_sessionid: str | None = None
    instagram_2fa_seed: str | None = None
    instagram_proxy: str | None = None

    # Delays e Segurança
    request_delay_min: float = 3.0
    request_delay_max: float = 6.0
    max_search_rounds: int = 3

    # Diretórios
    instagram_session_dir: Path = Path("sessions")
    outputs_dir: Path = Path("outputs")


settings = Settings()
