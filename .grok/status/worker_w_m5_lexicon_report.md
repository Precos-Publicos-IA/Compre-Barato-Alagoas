# W-m5-lexicon report — Phase 5 Lexicon mining

**Worker:** W-m5-lexicon  
**Date:** 2026-07-23  
**Commit intent:** `feat(match): lexicon mining from outcomes + 10k`  
**Plan:** `docs/self-improving-matching-plan.md` §Phase 5

## Definition of success

| ID | Criterion | Evidence | Status |
|----|-----------|----------|--------|
| **5-S1** | `mine_match_lexicon.py` produces versioned JSON under `backend/data/matching/` with documented schema | `backend/data/matching/heads_lexicon.v1.json` (`schema_version`, `version`, `generated_at`, `source`, `heads`, …); schema in `backend/data/matching/README.md` | **PASS** |
| **5-S2** | Dry-run on CI fixture completes &lt; 60s, non-flaky | `tests/test_mine_match_lexicon.py::test_s1_s2_s7_dry_run_fixture` times subprocess; fixture `tests/fixtures/match_lexicon_mine_sample.jsonl` | **PASS** |
| **5-S3** | Miner never emits cross-head synonym pairs that fail heads_compatible | `filter_synonym_pairs` + `synonym_pair_safe`; tests drop queijo↔pao, frango↔pastel, maca↔macarrao | **PASS** |
| **5-S4** | Loading lexicon is opt-in; default = current intent | Env `MATCH_LEXICON_PATH` unset by default; `app/services/rag/lexicon.py`; tests load on/off | **PASS** |
| **5-S5** | With lexicon loaded, intent + relevance goldens green | `MATCH_LEXICON_PATH=data/matching/heads_lexicon.v1.json pytest tests/test_intent_heads.py tests/test_relevance_quality.py` exit 0 | **PASS** |
| **5-S6** | Promotion path documented: raw miner ≠ auto-merge | `backend/data/matching/README.md` promotion section; miner always writes `promoted_synonym_groups: []` | **PASS** |
| **5-S7** | Mined heads contain staples (arroz, feijao, leite, …) on 10k | Spot-check `heads_lexicon.v1.json`: arroz/feijao/leite/pao/cafe/ovo present; also covered on CI fixture | **PASS** |

## Deliverables

| Path | Role |
|------|------|
| `backend/scripts/mine_match_lexicon.py` | Miner CLI |
| `backend/app/services/rag/lexicon.py` | Opt-in loader |
| `backend/app/services/rag/intent.py` | `expand_synonyms` uses **promoted** groups only when loaded |
| `backend/data/matching/heads_lexicon.v1.json` | Mined artifact from 10k |
| `backend/data/matching/README.md` | Schema + promotion runbook |
| `backend/tests/fixtures/match_lexicon_mine_sample.jsonl` | CI dry-run fixture |
| `backend/tests/test_mine_match_lexicon.py` | 5-S* unit coverage |
| `.env.example` | Documents `MATCH_LEXICON_PATH` |

## Safety

- `synonym_candidates` never applied at runtime.
- Only explicit `promoted_synonym_groups` (post-review) enter `expand_synonyms`.
- Cross-head poison filtered at mine time and locked by unit tests.

## Pytest (local)

```text
pytest tests/test_mine_match_lexicon.py tests/test_intent_heads.py \
       tests/test_relevance_quality.py tests/test_learn_policy.py -q
# all green
```

## Out of scope (per brief)

- M3/M4 re-open
- B2 live SEFAZ re-smoke (W-b2-resmoke)
- UI matrix
