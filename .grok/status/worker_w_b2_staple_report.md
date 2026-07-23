# W-b2-staple — staple fetch reliability

**Date:** 2026-07-23  
**Worker:** W-b2-staple  
**Status:** SHIPPED (code + tests; live prewarm runs on next backend/deploy restart)

## Problem

Popular staples (arroz, feijão, leite, …) often paid full cold SEFAZ cost under multi-item load and hit `sefaz_item_deadline_seconds=55` → `items_fetch_failed`, looking like empty catalog. Prewarm scripts existed but were not run post-deploy; Flutter ignored `items_fetch_failed` / `fetch_failed_labels`.

## What changed

| Area | Change |
|------|--------|
| Shared list | `backend/app/services/sefaz/staples.py` — expanded RAG mappings + 20-term `STAPLE_FETCH_TERMS` |
| Python prewarm | `backend/scripts/prewarm_staples.py` — uses shared list; safer default `--batch-size 1` + delay; `--skip-rag` |
| Deploy hook | `deploy/prewarm-staples.sh` — curl-only API warm (no Python on VPS) |
| Post-health | `deploy/remote-update.sh` runs prewarm after `/health` when `PREWARM_STAPLES=1` (default) |
| CI | `.github/workflows/deploy.yml` documents/enables `PREWARM_STAPLES=1` on stack restart |
| Flutter | Parse `items_fetch_failed` / `fetch_failed_labels`; banner + empty-state copy distinguishes upstream fail vs true missing |
| Empty cache | Reconfirmed via tests: successful hits stick; empty/fail never cached |

## SHA

`9ec6775` (pushed to `main`)

## How to verify

```bash
# Unit
cd backend && PYTHONPATH=. pytest tests/test_prewarm_staples.py tests/test_empty_cache.py -q
cd frontend && flutter test test/models_test.dart

# Local API warm (optional)
API_BASE=http://127.0.0.1:8000 bash deploy/prewarm-staples.sh

# After deploy to VPS: remote-update log should show
#   "==> Post-health staple prewarm"
# Then warm probe (expect items_fetch_failed=0 for staples when SEFAZ healthy):
curl -sS -X POST https://alagoas.precospublicos.ia.br/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{"items":["arroz","feijao","leite"],"latitude":-9.6633,"longitude":-35.7089,"radius_km":8,"days":7}' \
  | jq '.metrics | {items_fetch_failed, fetch_failed_labels, match_rate}'
```

## Residual / hard-blocks

| Item | Notes |
|------|--------|
| First post-deploy prewarm wall time | ~20 terms × (SEFAZ RTT + 1.5s delay); non-fatal if SEFAZ flakes (`PREWARM_STRICT=0`) |
| Live SEFAZ empty for some hygiene terms | Still true no_data when API returns empty — prewarm cannot invent products |
| RAG seed on VPS | Shell prewarm only hits search API (warms term cache + organic RAG on success). Full Redis RAG seed still needs `python scripts/prewarm_staples.py` with `REDIS_URL` (optional ops) |
| Head-alignment | Untouched (K1 shipped separately) |

## Acceptance vs plan B2

| Criterion | Status |
|-----------|--------|
| Expand staple/popular prewarm list | Done |
| Deploy actually runs prewarm when stack restarts | Done (`remote-update.sh`) |
| Safer batching (no stampede during warm) | Done (batch size 1 default) |
| UI distinguishes fetch_failed vs empty | Done |
| Never cache empty failures | Still true + regression test |
| Warm p95 &lt; 45s / failed=0 on prod | Needs post-deploy live probe (ops/K5) |
