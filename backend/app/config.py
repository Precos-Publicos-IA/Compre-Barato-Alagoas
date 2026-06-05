"""Application settings.

Everything is driven by environment variables so the same image can run in mock
mode (no SEFAZ token, no external infra) or fully wired in production by flipping a
few flags. See ``.env.example`` at the repo root for the full list.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Maceió city center — used as the default search origin (manual Anexo II IBGE 2704302).
MACEIO_LAT = -9.6498
MACEIO_LON = -35.7089
MACEIO_IBGE = "2704302"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "Compre Barato Alagoas"
    environment: str = "development"
    log_level: str = "INFO"
    # Comma-separated list of allowed CORS origins; "*" allows all (dev only).
    cors_origins: str = "*"

    # --- Mock flags (the heart of the "build first, get token later" strategy) ---
    use_mock_sefaz: bool = True
    use_mock_llm: bool = True

    # --- SEFAZ Economiza Alagoas API (only used when use_mock_sefaz is False) ---
    sefaz_base_url: str = (
        "http://api.sefaz.al.gov.br/sfz-economiza-alagoas-api/api/public/"
    )
    sefaz_app_token: str = ""  # secret; server-side only, never sent to clients
    sefaz_timeout_seconds: float = 15.0

    # --- LLM (Claude Haiku) — only used when use_mock_llm is False ---
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"

    # --- Search defaults / SEFAZ-imposed limits ---
    default_radius_km: int = 8       # SEFAZ allows 1..15
    default_days: int = 7            # SEFAZ allows 1..10
    records_per_page: int = 500      # SEFAZ allows 50..5000
    top_stores: int = 5             # how many ranked stores we return by default

    # --- Cache (Redis optional; falls back to in-process memory) ---
    redis_url: str = ""
    cache_ttl_seconds: int = 6 * 60 * 60  # 6h; data reflects last <=10 days of sales

    # --- Rate limiting ---
    daily_search_limit: int = 300    # per client per day; 0 disables

    # --- Database (Postgres + pgvector) — optional; core flow works without it ---
    database_url: str = ""

    # --- Observability (no-op when unset) ---
    sentry_dsn: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
