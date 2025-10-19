"""
Configuration settings for the Lingolino API.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    app_name: str = "Lingolino API"
    app_version: str = "0.1.0"
    debug: bool = False

    # CORS Settings
    cors_origins: list[str] = ["*"]  # Configure for production
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # LLM Settings
    llm_model: str = "google_genai:gemini-2.0-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields from .env (like GOOGLE_API_KEY, LANGSMITH_*, etc.)
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
