# Training datasets — Compre Barato Alagoas

Live `POST /api/v1/search` captures for model / ranking / RAG training.

**Shipped:** `alagoas_search_10k.jsonl` + manifest are committed (≈39 MB). Logs and plan files stay local (see `.gitignore`).

## Files

| File | Purpose | In git? |
|------|---------|---------|
| `alagoas_search_10k.jsonl` | One JSON object per line: request + full API response | yes |
| `alagoas_search_10k.manifest.json` | Run summary (counts, sources, places) | yes |
| `README.md` | This file | yes |
| `alagoas_search_10k.plan.json` | Deterministic sample plan | no (local) |
| `collect.log` | Collector progress log | no |

## Record shape

```json
{
  "id": "sha1-prefix",
  "collected_at": "ISO-8601",
  "latency_ms": 1234,
  "http_status": 200,
  "error": null,
  "request": {
    "items": ["arroz"],
    "latitude": -9.66162,
    "longitude": -35.74925,
    "radius_km": 8,
    "days": 7
  },
  "meta": {
    "base_query": "arroz",
    "category": "staples",
    "base_id": 1,
    "place_hint": "Maceió - Centro"
  },
  "response": { "...SearchResponse..." },
  "summary": {
    "data_source": "web",
    "stores_found": 5,
    "match_rate": 1.0,
    "top_store": "...",
    "top_description": "..."
  }
}
```

## Rebuild / resume

```bash
# From repo root — resume-safe (skips successful ids already in JSONL)
python3 backend/scripts/build_training_dataset.py --target 10000 --concurrency 4
```

Uses 40 Alagoas anchors + small jitter and query variants over `shopping_list_100.json`.
Requires ops egress IP in `RATELIMIT_WHITELIST_IPS` when daily limits apply.

Locations are all inside Alagoas. Upstream is SEFAZ/web; be polite with concurrency.
