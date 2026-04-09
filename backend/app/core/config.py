"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──
    app_name: str = "Logistics Presale AI System"
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-this-to-a-random-secret-key"
    cors_origins: str = "http://localhost:3000"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/logistics_presale"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── LLM ──
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    gemini_api_key: str = ""
    minimax_api_key: str = ""
    glm_api_key: str = ""

    llm_primary_model: str = "claude-sonnet-4-20250514"
    llm_fallback_model: str = "gpt-4o"

    # ── Vector DB ──
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    embedding_model: str = "text-embedding-3-small"

    # ── Object Storage ──
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "logistics-presale"

    # ── Agent ──
    agent_default_timeout_minutes: int = 10
    agent_max_retries: int = 2
    default_language: str = "zh"  # zh = 中文, en = English

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
