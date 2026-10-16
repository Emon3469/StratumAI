from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

PLACEHOLDER_PREFIXES = ("your_", "sk-your", "changeme", "xxx")


def _clean_secret(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().strip('"').strip("'")
    if not value or value.lower().startswith(PLACEHOLDER_PREFIXES):
        return None
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "StratumAI"
    environment: str = Field(default="development", alias="APP_ENV")

    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    allowed_origin_regex: str | None = r"https://.*\.vercel\.app"
    rate_limit_per_minute: int = 30

    groq_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: str | None = None

    groq_model: str = "openai/gpt-oss-120b"
    groq_backup_models: str = "openai/gpt-oss-20b"
    groq_fast_model: str = "qwen/qwen3.8-27b"
    groq_guard_model: str = "meta-llama/llama-prompt-guard-2-86m"
    openai_model: str = "gpt-4.1-mini"
    openai_fast_model: str | None = "gpt-4.1-nano"
    anthropic_model: str = "claude-haiku-4-5"
    gemini_model: str = "gemini-flash-lite-latest"
    gemini_backup_models: str = "gemini-flash-latest"

    llm_fallback_order: str = "groq,openai,anthropic,gemini"
    llm_timeout_seconds: float = 25.0
    llm_first_token_timeout_seconds: float = 12.0
    llm_max_output_tokens: int = 1200
    llm_cooldown_seconds: float = 20.0
    planner_budget_seconds: float = 2.5
    llm_cache_ttl_seconds: int = 900
    llm_cache_size: int = 256

    guard_enabled: bool = True
    guard_threshold: float = 0.85

    qdrant_url: str | None = Field(default=None, alias="QDRANT_CLUSTER_ENDPOINT")
    qdrant_api_key: str | None = None
    qdrant_collection: str = "stratumai_kb"

    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    retrieval_candidates: int = 12
    retrieval_top_k: int = 5
    max_context_chars: int = 9000
    max_history_messages: int = 10

    logfire_token: str | None = None

    @field_validator(
        "groq_api_key",
        "openai_api_key",
        "anthropic_api_key",
        "gemini_api_key",
        "qdrant_api_key",
        "logfire_token",
        mode="before",
    )
    @classmethod
    def _secrets(cls, value: str | None) -> str | None:
        return _clean_secret(value)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def fallback_order(self) -> list[str]:
        return [p.strip().lower() for p in self.llm_fallback_order.split(",") if p.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
