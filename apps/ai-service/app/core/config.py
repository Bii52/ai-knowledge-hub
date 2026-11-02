from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    ENVIRONMENT: str = Field(default="development", description="Environment mode (development/production)")
    HOST: str = Field(default="0.0.0.0", description="Host to bind the server")
    PORT: int = Field(default=8000, description="Port to run the service")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Allowed CORS origins",
    )

    # Database Configuration (Supabase PostgreSQL + pgvector)
    DATABASE_URL: str = Field(
        default="",
        description="PostgreSQL connection string with pgvector support",
    )

    # Supabase Object Storage (S3-compatible)
    STORAGE_ENDPOINT_URL: str = Field(default="", description="Supabase S3 storage endpoint URL")
    STORAGE_REGION: str = Field(default="eu-west-1", description="Storage region")
    STORAGE_ACCESS_KEY: str = Field(default="", description="S3 Access Key ID")
    STORAGE_SECRET_KEY: str = Field(default="", description="S3 Secret Access Key")
    STORAGE_BUCKET_NAME: str = Field(default="ai-knowledge-hub", description="Bucket name for documents")

    # Embeddings & AI Model
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Model name for generating embeddings")
    EMBEDDING_DIMENSION: int = Field(default=1536, description="Vector dimension size for pgvector")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key for embeddings and completions")

    model_config = SettingsConfigDict(
        env_file=(_ENV_PATH, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()

