# Backend — Compre Barato Alagoas

FastAPI service that acts as a secure intermediary over the SEFAZ-AL Economiza Alagoas
public price API. See the [root README](../README.md) for the full picture.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"     # ".[prod]" adds redis/postgres/anthropic/sentry/langfuse
pytest
uvicorn app.main:app --reload
```

Runs with **zero external infra** in mock mode (in-memory cache, mock SEFAZ + LLM).
Configuration is via environment variables — see [`../.env.example`](../.env.example).

## Module map

| Path | Responsibility |
|------|----------------|
| `app/config.py` | settings + mock flags |
| `app/services/sefaz/` | SEFAZ client (Protocol + mock + HTTP API + website scrape + factory) |
| `app/services/llm/` | list parser (Protocol + mock + Claude + factory) |
| `app/services/normalization/` | quantity extraction, unit conversion, fair pricing |
| `app/services/ranking.py` | aggregate offers into ranked store baskets |
| `app/services/search_service.py` | end-to-end orchestration + caching |
| `app/api/routes/` | `/health`, `/api/v1/search`, `/api/v1/suggestions` |
| `app/cache.py` | Redis or in-memory cache + daily rate limit |
| `app/data/mock_sefaz.json` | synthetic Maceió catalog for mock mode |
