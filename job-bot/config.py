import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str | None = None
    API_URL: str = "http://localhost:8000/api/v1"

    log_level: str = "INFO"

    _env = os.getenv("APP_ENV", "dev")
    _env_file = ".env.prod" if _env == "prod" else ".env.dev"

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        env_nested_delimiter="_",
    )

settings = Settings()