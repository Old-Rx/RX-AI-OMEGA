from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RX_", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./data/rx_ai_omega.db"
    auth_secret: str = "development-only-insecure-secret"
    access_token_minutes: int = 60
    bootstrap_admin_username: str | None = "admin"
    bootstrap_admin_password: str | None = "change-me-now"
    provider: Literal["mock", "openai", "ollama"] = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    memory_backend: Literal["local", "qdrant"] = "local"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    execution_backend: Literal["local", "redis"] = "local"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    log_level: str = "INFO"
    auto_create_schema: bool = True

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.environment == "production":
            if len(self.auth_secret) < 32 or "change-me" in self.auth_secret:
                raise ValueError("RX_AUTH_SECRET must be a strong secret in production")
            if self.bootstrap_admin_password == "change-me-now":
                raise ValueError("default bootstrap password is forbidden in production")
            if self.database_url.startswith("sqlite"):
                raise ValueError("production requires PostgreSQL; SQLite is a development profile")
        if self.provider == "openai" and not self.openai_api_key:
            raise ValueError("RX_OPENAI_API_KEY is required when RX_PROVIDER=openai")
        return self

    def ensure_local_directories(self) -> None:
        if self.database_url.startswith("sqlite:///") and ":memory:" not in self.database_url:
            Path(self.database_url.removeprefix("sqlite:///")).parent.mkdir(
                parents=True, exist_ok=True
            )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
