"""
Configuration settings for the Lingolino API.
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
from typing import Union
import json


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    app_name: str = "Lingolino API"
    app_version: str = "0.1.0"
    debug: bool = False

    # CORS Settings
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, list]) -> list[str]:
        """Parse CORS origins from JSON string, comma-separated string, or list."""
        if isinstance(v, str):
            # Try parsing as JSON first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

            # Fallback to comma-separated
            return [origin.strip() for origin in v.split(',') if origin.strip()]

        return v if isinstance(v, list) else [v]

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # LLM Settings
    llm_model: str = "google_genai:gemini-2.0-flash"

    # AWS S3 Settings for Dynamic Prompts (Public Bucket)
    aws_s3_bucket_name: str = "conversational-ai-prompts-bucket/"
    aws_s3_prompts_prefix: str = "prompts/"
    aws_region: str = "eu-central-1"

    # Prompt Configuration
    use_s3_prompts: bool = False
    prompts_cache_ttl: int = 60

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        # Disable automatic JSON parsing for list/dict fields
        json_schema_extra={
            "env_parse_none_str": None
        }
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
