"""Application settings.

Everything is driven by environment variables so the same image can run in mock
mode (no SEFAZ token, no external infra) or fully wired in production by flipping a
few flags. See ``.env.example`` at the repo root for the full list.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Default search origin (busy Pajuçara / orla neighborhood). Must stay in sync
# with frontend/lib/core/location.dart:kMaceioDefault so that location-denied
# users and backend fallbacks see comparable results and radius filtering.
MACEIO_LAT = -9.6633
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
    # Interactive API docs (Swagger / ReDoc / openapi.json). Empty = auto:
    # off in production, on otherwise. Set true/false to override explicitly.
    expose_api_docs: str = ""

    # --- Mock flags (the heart of the "build first, get token later" strategy) ---
    use_mock_sefaz: bool = True
    use_mock_llm: bool = True

    # --- SEFAZ Economiza Alagoas API (only used when use_mock_sefaz is False) ---
    sefaz_base_url: str = (
        "http://api.sefaz.al.gov.br/sfz-economiza-alagoas-api/api/public/"
    )
    # Legacy/bootstrap fallback only. Prefer setting the token via the admin panel
    # (encrypted in Redis, never on disk). Leave empty in production.
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
    # Per-item items are fetched concurrently to cut wall time for cold baskets;
    # bound the fan-out so we stay polite to SEFAZ.
    sefaz_concurrency: int = 6
    # How many SEFAZ result pages to pull per item (>1 follows totalPaginas).
    # 1 keeps today's single-page behaviour; the mock always returns one page.
    max_sefaz_pages: int = 1

    # --- Cache + storage (Redis is MANDATORY; the app fails fast without it) ---
    # Holds the search cache, shareable-list UUIDs, device records and rate limits.
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 6 * 60 * 60  # 6h; data reflects last <=10 days of sales

    # --- Privacy (LGPD) ---
    # Bump when the privacy policy / terms change; stored with each consent record.
    # Keep in lockstep with frontend AppConfig.policyVersion and .env.example.
    policy_version: str = "2026-06-06"

    # --- Rate limiting ---
    daily_search_limit: int = 300    # per client per day; 0 disables
    # Comma-separated peer IPs allowed to supply X-Forwarded-For for rate-limit
    # identity (typically loopback / docker gateway where host nginx terminates TLS).
    # Empty => never trust XFF; always use request.client.host (safe default for
    # direct gunicorn access). Production behind nginx on 127.0.0.1:8000 should set
    # TRUSTED_PROXY_IPS=127.0.0.1,::1 (see #264).
    trusted_proxy_ips: str = "127.0.0.1,::1"

    # --- Admin dashboard ---
    # Bearer token guarding /admin/api/*. Empty => admin API is disabled (401).
    admin_token: str = ""
    # Per admin-token hash + IP bucket; higher than public search to allow dashboards.
    # 0 disables admin rate limiting (#266). Failed auth is still cheap (hmac only).
    admin_hourly_request_limit: int = 1200

    # --- Secret store (encryption at rest for runtime-managed secrets) ---
    # Fernet key (urlsafe-base64, 32 bytes) used to encrypt secrets entered via the
    # admin panel (e.g. the SEFAZ token) before they are stored in Redis. Generate
    # once: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    # Empty => the admin secret panel is disabled; SEFAZ falls back to sefaz_app_token.
    secret_encryption_key: str = ""

    # --- Database (Postgres + pgvector) — optional; core flow works without it ---
    database_url: str = ""

    # --- Observability (no-op when unset) ---
    sentry_dsn: str = ""
    # 0..1 fraction of transactions to send when Sentry is enabled (#267).
    sentry_traces_sample_rate: float = 0.0
    # Optional release tag (git sha / image tag). Empty => omit.
    git_sha: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # --- Client policy (public; app/web may gate outdated builds later — #268) ---
    # Semver strings; empty => not enforced (endpoint still reports them as null).
    min_app_version: str = ""
    min_web_build: str = ""
    client_update_message: str = (
        "Atualize o app ou recarregue a página para continuar usando o Compre Barato Alagoas."
    )
    client_update_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def trusted_proxy_ip_set(self) -> set[str]:
        return {p.strip() for p in self.trusted_proxy_ips.split(",") if p.strip()}

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"prod", "production"}

    @property
    def api_docs_enabled(self) -> bool:
        """Whether /docs, /redoc and /openapi.json are mounted.

        Default: enabled outside production (local dev, tests). In production the
        interactive OpenAPI UI is off so scanners and casual browsers don't get a
        free attack map; the *application* API remains intentionally public for
        the Flutter client. Override with EXPOSE_API_DOCS=true|false.
        """
        raw = (self.expose_api_docs or "").strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"0", "false", "no", "off"}:
            return False
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()
