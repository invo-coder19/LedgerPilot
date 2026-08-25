"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "LedgerPilot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ledgerpilot"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET: str = "changeme-use-a-long-random-string-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ── CORS ──────────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://frontend:5173",
    ]

    # ── Seed credentials ──────────────────────────────────────────────────────
    SEED_ADMIN_PASSWORD: str = "Admin@123"
    SEED_MANAGER_PASSWORD: str = "Manager@123"
    SEED_ANALYST_PASSWORD: str = "Analyst@123"
    SEED_VIEWER_PASSWORD: str = "Viewer@123"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
