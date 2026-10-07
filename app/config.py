from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "postgresql://chatbot:chatbot@postgres:5432/chatbot"
    session_secret: str = Field(min_length=32)

    # AI 공급자(Codyssey "Neito" 게이트웨이) 연동 설정.
    # ai_api_key는 기본값이 없어서, .env에 안 넣으면 앱 시작 시점에 바로 에러가 난다.
    ai_api_key: str = Field(min_length=1)
    ai_base_url: str = "https://copa.codyssey.kr"
    ai_model: str = "claude-haiku-4"
    ai_timeout_seconds: float = 10.0

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
