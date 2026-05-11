"""
Central application configuration.

Reads settings from .env file via pydantic-settings.
Provides a typed `settings` object used throughout the codebase.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Supabase ---
    supabase_url: str = Field(default="", description="https://xxx.supabase.co")
    supabase_anon_key: str = Field(default="", description="anon public key")
    supabase_service_key: str = Field(default="", description="service_role secret key")
    supabase_jwt_secret: str = Field(default="", description="JWT secret for token verification")

    # --- Direct Postgres ---
    database_url: str = Field(default="")

    # --- API server ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    # Optional regex (Starlette CORSMiddleware), e.g. https://.*\.vercel\.app for Vercel previews
    cors_origin_regex: str = ""

    # --- ML Models ---
    max_reviews_per_analysis: int = 10000
    min_reviews_for_topics: int = 10
    sentiment_model: str = "distilbert-base-uncased-finetuned-sst-2-english"
    sentiment_model_multilingual: str = "nlptown/bert-base-multilingual-uncased-sentiment"
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Storage ---
    storage_bucket: str = "reviews"
    local_upload_dir: str = "data/raw"

    # --- Reports ---
    report_language: str = "en"
    pdf_font: str = "Helvetica"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_dir(self) -> Path:
        path = PROJECT_ROOT / self.local_upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
