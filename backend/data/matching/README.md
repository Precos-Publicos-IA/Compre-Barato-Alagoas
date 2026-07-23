# Matching measure scripts (Phase 4)

Self-improving matching loop — **measure** track.

| Script | When | Network |
|--------|------|---------|
| `backend/scripts/offline_rescore_match.py` | Every scorer change / CI or nightly | **No** |
| `backend/scripts/match_live_smoke.py` | **Post-deploy only** | Yes (SEFAZ via API) |

Live smoke is **not** part of default unit `pytest` / every-push CI (SEFAZ 429 flakiness).

## Offline rescore

Rescores stored tops from the committed fixture (or honest eval JSON) with the
current `score_description` + `auto_label`.

```bash
# from repo root
PYTHONPATH=backend python3 backend/scripts/offline_rescore_match.py --help

PYTHONPATH=backend python3 backend/scripts/offline_rescore_match.py \
  --input backend/tests/fixtures/match_offline_tops.json \
  --out .grok/status/match_offline_rescore_$(date -u +%Y%m%d).json \
  --write-notes
```

### Artifact summary fields (4-S2)

| Field | Meaning |
|-------|---------|
| `n` | Queries rescored (with tops) |
| `still_bad` | Live-bad rows whose top1 is still hard-reject/bad (not emptied) |
| `now_empty_or_reject` | Live-bad rows whose all tops would be filtered (improvement) |
| `regressed_good_to_bad` | Live-good rows whose top1 is now bad/empty offline |

Also: `poison_pair_checks` for known head-incident pairs (4-S3).

Committed fixture: `backend/tests/fixtures/match_offline_tops.json`  
(source: honest tops subset; no SEFAZ payloads).

## Live smoke (post-deploy)

Serial **CONCURRENCY=1**, default **15** queries (staples + head incidents).

```bash
API_BASE=https://alagoas.precospublicos.ia.br \
  PYTHONPATH=backend python3 backend/scripts/match_live_smoke.py \
  --api "$API_BASE" \
  --out .grok/status/match_live_smoke_$(date -u +%Y%m%d).json \
  --write-md

# Sanity only (no HTTP):
PYTHONPATH=backend python3 backend/scripts/match_live_smoke.py --dry-run
```

### Summary fields (4-S5)

| Field | Track |
|-------|--------|
| `fetch_fail_rate` | Fetch (items_fetch_failed / upstream empty) |
| `found_rate` | Found tops with stores |
| `good_top_rate` / `weak_top_rate` / `bad_top_rate` | **Among found** (match track via `auto_label`) |

Do not mix fetch empties into “bad match.”

## CI policy

| Check | When |
|-------|------|
| `pytest` (intent, relevance, labeler, learn_policy, offline fixture test) | every push |
| offline rescore vs committed fixture | optional in unit test (no network) |
| live smoke | **post-deploy only** |
