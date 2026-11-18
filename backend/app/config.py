"""Application settings, loaded from environment variables or a .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # Which LLM answers questions. "auto" picks Claude, then Gemini, then demo mode.
    llm_provider: Literal["auto", "claude", "gemini", "demo"] = "auto"

    anthropic_api_key: str | None = None
    claude_model: str = "claude-haiku-5-5"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Storage and ingestion
    data_dir: Path = Path("data")
    max_upload_mb: int = 20
    chunk_size: int = 900  # characters
    chunk_overlap: int = 150

    # Retrieval
    top_k: int = 5

    # Comma-separated list of allowed frontend origins (for local dev).
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def resolved_provider(self) -> str:
        if self.llm_provider != "auto":
            return self.llm_provider
        if self.anthropic_api_key:
            return "claude"
        if self.gemini_api_key:
            return "gemini"
        return "demo"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "hujjat.db"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
