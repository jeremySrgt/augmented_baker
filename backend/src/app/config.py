from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_BACKEND_DIR / ".env", extra="ignore")

    APP_NAME: str = "augmented-baker"
    ENV: str = "dev"
    LOG_LEVEL: str = "info"

    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_API_KEY: SecretStr | None = None

    NOTION_TOKEN: SecretStr | None = None

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: SecretStr | None = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM: str = "Madeleine Croûton <madeleine@chez-madeleine.test>"
    SMTP_DRY_RUN: bool = False
    SMTP_REDIRECT_TO: str | None = None

    MEMORY_DB_PATH: Path = _BACKEND_DIR / "data" / "conversations.sqlite"


settings = Settings()
