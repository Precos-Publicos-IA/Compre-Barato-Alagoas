# Matching data & measure scripts (Phases 4–5)

Self-improving matching loop — **measure** (Phase 4) and **lexicon mining** (Phase 5).

| Script | When | Network |
|--------|------|---------|
| `backend/scripts/offline_rescore_match.py` | Every scorer change / CI or nightly | **No** |
| `backend/scripts/match_live_smoke.py` | **Post-deploy only** | Yes (SEFAZ via API) |
| `backend/scripts/mine_match_lexicon.py` | Manual / nightly / CI dry-run on fixture | **No** |

Live smoke is **not** part of default unit `pytest` / every-push CI (SEFAZ 429 flakiness).

---

## Phase 5 — Lexicon mining

### Artifact

Versioned JSON under this directory, e.g. `heads_lexicon.v1.json`.

| Field | Meaning |
|-------|---------|
| `schema_version` | Integer schema id (currently `1`) |
| `version` | Lexicon edition string (`v1`, `v2`, …) |
| `generated_at` | UTC ISO timestamp |
| `source` | Input paths + kind (`jsonl_training_or_outcomes`) |
| `heads` | `[{token, count, as_query, as_desc}, …]` mined heads |
| `synonym_candidates` | Head-safe co-success pairs (**candidates only**) |
| `brand_skip_hints` | Frequent brand-first desc tokens (hints) |
| `promoted_synonym_groups` | **Reviewed** groups only; miner always writes `[]` |
| `meta` | Counts, thresholds, safety note |

### Runbook

```bash
# CI / dry-run on committed fixture (< 60s, no network)
PYTHONPATH=backend python3 backend/scripts/mine_match_lexicon.py \
  --input backend/tests/fixtures/match_lexicon_mine_sample.jsonl \
  --out /tmp/heads_lexicon.dry.json \
  --dry-run --min-head-count 1

# Full mine from 10k training log
PYTHONPATH=backend python3 backend/scripts/mine_match_lexicon.py \
  --input backend/data/training-datasets/alagoas_search_10k.jsonl \
  --out backend/data/matching/heads_lexicon.v1.json \
  --min-head-count 3 --min-co-success 2
```

Optional outcome-log JSONL can be passed with additional `--input` paths.

### Promotion path (5-S6) — **raw miner ≠ production synonyms**

```text
mine_match_lexicon.py
        │
        ▼
 heads_lexicon.vN.json
   heads[]                  → review / analytics (informational)
   synonym_candidates[]     → REVIEW QUEUE only
   promoted_synonym_groups  → always [] from miner
        │
        │  human (or strict second-pass) review
        │  - drop weak / brand noise
        │  - confirm heads_compatible + product identity
        │  - never promote queijo↔pao-class pairs
        ▼
 edit promoted_synonym_groups: [["ovo","ovos"], ...]
   OR merge into intent.py _SYN_GROUPS after review
        │
        ▼
 opt-in load: MATCH_LEXICON_PATH=/path/to/heads_lexicon.vN.json
```

**Rules:**

1. **Never** auto-merge `synonym_candidates` into `_SYN_GROUPS` or into
   `promoted_synonym_groups` without review.
2. Runtime load is **opt-in** via env `MATCH_LEXICON_PATH`. Default (unset) =
   hard-coded intent only (current behavior).
3. When loaded, only `promoted_synonym_groups` participate in `expand_synonyms`.
   Raw `synonym_candidates` are ignored by the scorer.
4. Cross-head poison is filtered at mine time (`synonym_pair_safe` /
   `heads_compatible`); unit tests lock queijo↔pao etc.

### Optional load (5-S4)

```bash
# default — no lexicon
unset MATCH_LEXICON_PATH

# opt-in (after review; safe even with empty promoted groups)
export MATCH_LEXICON_PATH=backend/data/matching/heads_lexicon.v1.json
```

Loader: `app.services.rag.lexicon` (`load_match_lexicon`, `clear_match_lexicon`).

With lexicon loaded, property/goldens must stay green:

```bash
cd backend && PYTHONPATH=. pytest tests/test_intent_heads.py tests/test_relevance_quality.py -q
MATCH_LEXICON_PATH=data/matching/heads_lexicon.v1.json \
  PYTHONPATH=. pytest tests/test_intent_heads.py tests/test_relevance_quality.py -q
```

---

## Offline rescore (Phase 4)

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
| `pytest` (intent, relevance, labeler, learn_policy, offline, **mine lexicon**) | every push |
| offline rescore vs committed fixture | unit test (no network) |
| lexicon dry-run on fixture | unit test (no network, &lt; 60s) |
| live smoke | **post-deploy only** |
