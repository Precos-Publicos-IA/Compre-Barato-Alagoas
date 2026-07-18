# W-fix-empty-cache report (must-complete E)

**Worker:** W-fix-empty-cache  
**Date:** 2026-07-18  
**Status:** DONE `c92b9ba`

## Problem
1. Parallel web SEFAZ stampede returned empty under load/timeouts.
2. `fetch_offers` on exception returned `[]` (HTTP 200 “no products”).
3. **Empty successful scrapes were cached 6h** → ~200ms empty repeats poisoned evals/users.

Operator rejected “~71/100 missing SEFAZ rows” — staples like arroz exist.

## Fix
### `backend/app/services/search_service.py`
- **Do not cache** when `len(resp.conteudo)==0` (true empty / no_data).
- **Do not cache** on exception/timeout (already true; logs now say `upstream_failed, not caching`).
- **Read-side heal:** ignore + purge empty cache hits so already-poisoned Redis keys re-fetch.
- Track `labels_fetch_error` / `labels_fetch_ok`; final metrics only mark **upstream_failed** when every attempt failed (Verifier retry success clears failure).
- Analytics batch: `fetch_failed_labels` + `no_data_labels` split from flat `notfound_labels`.

### `backend/app/schemas/search.py`
- `SearchMetrics.items_fetch_failed: int = 0`
- `SearchMetrics.fetch_failed_labels: list[str] = []`
- Additive only — Flutter contract tests still pass (required keys unchanged).

### Tests `backend/tests/test_empty_cache.py`
| Test | Asserts |
|------|---------|
| `test_empty_sefaz_response_is_not_cached` | empty not in Redis; next search re-hits SEFAZ |
| `test_failed_fetch_is_not_cached_and_signals_upstream_failed` | no sefaz:search keys; metrics expose failed labels |
| `test_non_empty_response_is_cached` | non-empty still full-TTL cache hit |
| `test_poisoned_empty_cache_entry_is_ignored_and_purged` | pre-seeded empty ignored + replaced |
| `test_true_empty_is_no_data_not_fetch_failed` | clean empty → items_fetch_failed=0 |

## Verification
```
cd backend && python -m pytest tests/test_empty_cache.py tests/test_partial_results.py tests/test_api_contract.py tests/test_api.py -q
# 14 passed
```

## Out of scope (per brief)
- Full 100 live eval (quota 429)
- Full matrix
- Foreign projects

## Deploy note
After push → deploy, existing prod Redis empty poisons are healed on first read (purge + re-fetch). No manual Redis FLUSH required for this path.
