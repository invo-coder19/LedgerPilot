"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
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

    # ── Phase 3A: ML ──────────────────────────────────────────────────────────
    MODELS_DIR: str = "models"
    ML_RANDOM_SEED: int = 42
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    OPENAI_API_KEY: str = ""

    # ── Phase 3B: LLM / Agent ─────────────────────────────────────────────────
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = ""
    AI_MAX_CONTEXT_ITEMS: int = 20
    AI_MAX_TOOL_CALLS: int = 15
    AI_CONFIDENCE_HIGH: float = 0.90
    AI_CONFIDENCE_MEDIUM: float = 0.70

    @property
    def models_path(self) -> Path:
        """Absolute path to the models directory."""
        p = Path(self.MODELS_DIR)
        if not p.is_absolute():
            # Resolve relative to the backend/ directory
            p = Path(__file__).resolve().parent.parent.parent / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def effective_llm_model(self) -> str:
        """Return the model name, falling back to a sensible default."""
        if self.LLM_MODEL:
            return self.LLM_MODEL
        return "gemini-2.0-flash" if self.LLM_PROVIDER == "gemini" else "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()

