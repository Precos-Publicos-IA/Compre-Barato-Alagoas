# W-m0-m1 — Phase 0 + Phase 1 success map

| Field | Value |
|-------|--------|
| **Worker** | W-m0-m1 |
| **When (UTC)** | 2026-07-23 |
| **Ship SHA** | `5a16961577972e60a4467559569e522fd5b7e53e` (`5a16961`) |
| **Baseline SHA (pre)** | `bc5964f` |
| **Plan** | `docs/self-improving-matching-plan.md` |
| **Baseline note** | `.grok/status/match_baseline_phase0.md` |
| **Testing policy** | Backend/function first — pytest + TestClient; no UI matrix |

## Phase 0 — Definition of success

| ID | Criterion | Result | Evidence |
|----|-----------|:------:|----------|
| **0-S1** | Baseline snapshot with git SHA, date, overall eval pointer, found_rate / fetch_fail / p50–p95 | **PASS** | `.grok/status/match_baseline_phase0.md` + plan §14; eval C+ at `worker_w_eval_overall_report.md`; found 73.7%, fetch_fail 4/18 singles, p50~36.6s p95~55.7s |
| **0-S2** | `pytest tests/test_intent_heads.py tests/test_relevance_quality.py -q` green | **PASS** | Local run green on ship tree (with outcome_log suite) |
| **0-S3** | `MATCH_RULES_VERSION` stable non-empty string | **PASS** | `backend/app/services/rag/intent.py` → `"2026-07-23-head-v1"` |
| **0-S4** | Search API exposes `match_rules_version` on metrics | **PASS** | `SearchMetrics.match_rules_version`; TestClient `test_search_api_exposes_match_rules_version` |
| **0-S5** | No intentional matching score behavior change | **PASS** | Diff limited to version field plumbing, docs/baseline, outcome log (observe-only) |

**Phase 0: PASS**

## Phase 1 — Definition of success

| ID | Criterion | Result | Evidence |
|----|-----------|:------:|----------|
| **1-S1** | `outcome_log.py` with append + no-op modes | **PASS** | `backend/app/services/rag/outcome_log.py` |
| **1-S2** | With path set + sample 1.0, POST `/api/v1/search` appends ≥1 JSON line **per requested item** | **PASS** | `test_search_api_appends_outcome_when_path_set` (item-level rows) |
| **1-S3** | Path unset → search 200, no log file from sink | **PASS** | `test_search_api_noop_when_path_unset` + unit `test_append_and_noop` |
| **1-S4** | Lines include `ts`, `match_rules_version`, `query`, `items_fetch_failed`, `top_descriptions`, `stores_found` | **PASS** | schema tests + API test |
| **1-S5** | Never raw device_token / Authorization / SEFAZ app token | **PASS** | sanitize + refuse blob checks; API line grep |
| **1-S6** | Sample 0.0 → no lines for N searches | **PASS** | `test_sample_rate_zero_writes_nothing`, `test_search_api_sample_zero_no_lines` |
| **1-S7** | `.env.example` documents path + sample | **PASS** | root `.env.example` |
| **1-S8** | pytest green including outcome_log tests | **PASS** | `pytest tests/test_outcome_log.py tests/test_intent_heads.py tests/test_relevance_quality.py tests/test_api_contract.py -q` → all green |

**Phase 1: PASS**

## Wire points

| Path | Behavior |
|------|----------|
| `search_service.run_search` (final, non-partial) | `log_search_item_outcomes(...)` after metrics; never raises into client |
| `catalog/search` | same sink after metrics |
| Env | `MATCH_OUTCOME_LOG_PATH`, `MATCH_OUTCOME_LOG_SAMPLE` (default 1.0) |

## Aggregate schema note (1-S2)

Logging is **item-level**: one JSONL row per requested basket label (not one aggregate row per HTTP search). Documented in module docstring and plan Phase 1 schema.

## Out of scope (not done)

- M2 auto_label (field present as `"unknown"` placeholder)
- M3 learn_policy
- M4 offline rescore / live smoke scripts
- Flutter changes

## Commands

```bash
cd backend
pytest tests/test_outcome_log.py tests/test_intent_heads.py tests/test_relevance_quality.py tests/test_api_contract.py -q
```

## Git

```text
5a16961 feat(match): Phase 0+1 match_rules_version + search outcome log
```
