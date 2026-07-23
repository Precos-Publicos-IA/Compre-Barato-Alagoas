# W-m4-measure — Phase 4 offline rescore + live smoke

| Field | Value |
|-------|--------|
| **Worker** | W-m4-measure |
| **Ship SHA** | `cc2807fd97e890cce8b46189260fd79e2a8541e4` (`cc2807f`) |
| **When (UTC)** | 2026-07-23 |
| **Plan** | `docs/self-improving-matching-plan.md` Phase 4 |
| **Prior** | M0–M3 DONE (`5a16961` / `56ff4a5` / `3ae1f52`) |
| **Testing policy** | Backend/scripts only — no UI matrix; live smoke post-deploy only |

## Phase 4 — Definition of success

| ID | Criterion | Result | Evidence |
|----|-----------|:------:|----------|
| **4-S1** | `offline_rescore_match.py` runs against **committed fixture** and exits 0 | **PASS** | `backend/tests/fixtures/match_offline_tops.json` + `pytest tests/test_offline_rescore.py` |
| **4-S2** | Artifact counts: `n`, `still_bad`, `now_empty_or_reject`, `regressed_good_to_bad` | **PASS** | JSON schema in script docstring + `backend/data/matching/README.md` |
| **4-S3** | wrong_class tops → 0 still_bad; poison pairs OK; residual bound | **PASS** | still_bad=**0**, now_empty_or_reject=**20**/20 wrong_class; poison_pairs_all_ok; residual regressed_good_to_bad=**10** documented (stricter head on weak live-pass tops) |
| **4-S4** | `match_live_smoke.py` CONCURRENCY=1, ≥12 queries, JSON + optional md | **PASS** | default 15 queries; `--out` / `--write-md`; `--dry-run` in unit test |
| **4-S5** | Summary splits `fetch_fail_rate`, `found_rate`, `good_top_rate`/`weak_top_rate` among found | **PASS** | `summary` fields in script |
| **4-S6** | Live smoke **not** in default unit CI; docs say post-deploy only | **PASS** | deploy.yml only `pytest`; README + `--help` epilog; unit test uses `--dry-run` only |
| **4-S7** | One-line runbooks in `--help` or matching README | **PASS** | both scripts + `backend/data/matching/README.md` |
| **4-S8** | Backend pytest still green | **PASS** | `test_offline_rescore` + intent/relevance/labeler/learn_policy/outcome_log green |

**Phase 4: PASS**

## Offline summary numbers

Fixture: `backend/tests/fixtures/match_offline_tops.json` (91 queries with tops from honest eval)

| metric | value |
|--------|------:|
| n | 91 |
| still_bad | 0 |
| now_empty_or_reject | 20 |
| regressed_good_to_bad | 10 |
| good_to_good (+ weak) | 61 |
| poison_pairs_all_ok | true |

Artifacts:
- `.grok/status/match_offline_rescore_20260723.json`
- `.grok/status/match_offline_rescore_20260723.md`
- `.grok/status/match_offline_rescore_honest_20260723.json` (same tops from full honest JSON)

### Residual (4-S3 bound)

Live honest `pass` but current head rejects top1 (stricter match track — snack/pet/prepared bleed, not poison reintroduction):

manteiga→pipoca manteiga; requeijão→salg requeijão; presunto→flits; atum→whiskas; cenoura→pão; limão/laranja→suco cortesia; abóbora→plutonita; amendoim→paçoquita; creme dental→abbr hard-reject.

**wrong_class path:** 20/20 emptied (`still_bad=0`).

## Deliverables

| Path | Role |
|------|------|
| `backend/scripts/offline_rescore_match.py` | offline rescore, no network |
| `backend/scripts/match_live_smoke.py` | serial post-deploy smoke |
| `backend/tests/fixtures/match_offline_tops.json` | committed tops fixture |
| `backend/tests/test_offline_rescore.py` | CI: offline + dry-run smoke |
| `backend/data/matching/README.md` | runbooks + CI policy |

## Commands

```bash
# Offline (CI-safe)
PYTHONPATH=backend python3 backend/scripts/offline_rescore_match.py \
  --input backend/tests/fixtures/match_offline_tops.json \
  --out .grok/status/match_offline_rescore_$(date -u +%Y%m%d).json --write-notes

# Live smoke (POST-DEPLOY ONLY — not unit CI)
API_BASE=https://alagoas.precospublicos.ia.br \
  PYTHONPATH=backend python3 backend/scripts/match_live_smoke.py \
  --out .grok/status/match_live_smoke_$(date -u +%Y%m%d).json --write-md

# Unit
cd backend && PYTHONPATH=. pytest tests/test_offline_rescore.py \
  tests/test_labeler.py tests/test_intent_heads.py tests/test_relevance_quality.py \
  tests/test_learn_policy.py tests/test_outcome_log.py -q
```

## MVP checklist (M0–M4)

| Phase | Status |
|-------|--------|
| M0 match_rules_version + baseline | DONE |
| M1 outcome log | DONE |
| M2 auto_label | DONE |
| M3 learn_policy v2 | DONE |
| M4 offline rescore + live smoke | **DONE** (this report) |

Plan MVP-S1–S5 (observe → label → learn → measure scripts) closed for matching loop base.

## Out of scope

- Live production smoke HTTP run this turn (SEFAZ 429 risk; script ready for post-deploy)
- Phase 5 lexicon miner, Phase 6 Flutter feedback fields, Phase 7 model scorer
