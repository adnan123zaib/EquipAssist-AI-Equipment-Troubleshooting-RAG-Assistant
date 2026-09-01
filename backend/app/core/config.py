from functools import lru_cache
from pathlib import Path
import base64
import secrets

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "sqlite:///./equipment_rag.db"

    # LLM
    llm_provider: str = "local"
    llm_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Security
    jwt_secret_key: str | None = None
    app_encryption_key: str | None = None
    access_token_expire_minutes: int = Field(1440, ge=5, le=10080)

    # Embeddings
    embedding_provider: str = "local"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = Field(384, ge=256, le=384)

    # Vector database
    chroma_persist_directory: str = "./storage/chroma"

    # Manual storage
    manual_storage_directory: str = "./storage/manuals"

    # Chunking
    chunk_size: int = Field(1000, ge=200, le=4000)
    chunk_overlap: int = Field(150, ge=0, le=1000)

    # Retrieval
    retrieval_top_k: int = Field(6, ge=1, le=20)
    similarity_threshold: float = Field(0.35, ge=0, le=1)
    enable_reranking: bool = True
    max_retrieval_attempts: int = Field(2, ge=1, le=2)
    max_context_length: int = Field(12000, ge=1000)

    # Upload
    max_upload_size_mb: int = Field(30, ge=1, le=200)

    # Frontend
    frontend_url: str = "http://localhost:5173"

    @model_validator(mode="after")
    def validate_provider_keys(self):
        if self.llm_provider not in {"local", "groq", "openai", "anthropic"}:
            raise ValueError("LLM_PROVIDER must be 'local', 'groq', 'openai', or 'anthropic'")
        if self.embedding_provider != "local":
            raise ValueError("EMBEDDING_PROVIDER currently supports only 'local'")

        required_keys = {"groq": self.groq_api_key, "openai": self.openai_api_key, "anthropic": self.anthropic_api_key}
        if self.llm_provider in required_keys and not required_keys[self.llm_provider]:
            env_name = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[self.llm_provider]
            raise ValueError(f"{env_name} is required when LLM_PROVIDER={self.llm_provider}")

        if self.app_env in {"production", "staging"}:
            if not self.jwt_secret_key:
                raise ValueError("JWT_SECRET_KEY is required in production/staging")
            if not self.app_encryption_key:
                raise ValueError("APP_ENCRYPTION_KEY is required in production/staging")
        else:
            # Development/test instances get per-process secrets so a copied
            # example configuration never silently ships a known credential.
            if not self.jwt_secret_key:
                self.jwt_secret_key = secrets.token_urlsafe(48)
            if not self.app_encryption_key:
                self.app_encryption_key = base64.urlsafe_b64encode(
                    secrets.token_bytes(32)
                ).decode()

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        if self.embedding_dimension not in (256, 384):
            raise ValueError("EMBEDDING_DIMENSION must be either 256 or 384")
        return self

    def ensure_directories(self) -> None:
        Path(self.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
        Path(self.manual_storage_directory).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
