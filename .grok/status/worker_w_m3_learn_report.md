# W-m3-learn — Phase 3 learn_policy v2 success map

| Field | Value |
|-------|--------|
| **Worker** | W-m3-learn |
| **Ship SHA** | (see Git section — tip after wrong_item multi-target demote) |
| **Feature SHA** | `cf851c34f0709a95582970fd35756c1d53124a2c` (`cf851c3`) learn_policy v2 |
| **When (UTC)** | 2026-07-23 |
| **Plan** | `docs/self-improving-matching-plan.md` Phase 3 |
| **Testing policy** | Backend/function first — pytest only; no UI matrix |
| **Prior** | M2 `56ff4a5` auto_label |

## Phase 3 — Definition of success

| ID | Criterion | Result | Evidence |
|----|-----------|:------:|----------|
| **3-S1** | No direct `rag.record_success` from verifier/search outside `learn_policy` (primitives OK) | **PASS** | Verifier uses `on_search_item_result` only; feedback uses `on_user_feedback`; grep: only `store.py` (primitive), `learn_policy.py` (door), `cache.py` (prewarm/legacy wrapper). `test_s1_*` |
| **3-S2** | Positive learn **refuses** when `fetch_failed` set | **PASS** | `test_s2_fetch_failed_refuses_success` → `refused_fetch_failed`, empty lookup |
| **3-S3** | Positive learn **refuses** head-incompatible rewrite (peito→ovos, queijo→pão de queijo) | **PASS** | `test_s3_peito_ovos_never_stored`, `test_s3_queijo_pao_de_queijo_never_stored` |
| **3-S4** | Positive learn **refuses** when best desc has `alignment_verdict == reject` | **PASS** | `test_s4_alignment_reject_refuses` (queijo + PAO DE QUEIJO MINI) |
| **3-S5** | Positive learn **refuses** when score &lt; `min_score_to_learn` (0.50) | **PASS** | `test_s5_low_score_refuses`; also `test_s5_package_class_false_refuses` |
| **3-S6** | Positive learn **accepts** happy path and store shows mapping | **PASS** | `test_s6_happy_path_arroz_stores_mapping`; verifier funnel integration |
| **3-S7** | `on_user_feedback(kind=wrong_item)` demotes/removes and **never** success | **PASS** | `test_s7_wrong_item_demotes_never_success` (spy); item-only API clears all rewrites for query (`test_wrong_item_feedback_demotes_rag_mapping`) |
| **3-S8** | Env `MATCH_LEARN=0` makes learn_policy a **no-op** for writes | **PASS** | `test_s8_match_learn_off_no_writes` |
| **3-S9** | `pytest` green including `test_learn_policy.py` | **PASS** | full related suite green (see Commands) |

**Phase 3: PASS**

## Gates implemented (§3.2 positive)

All required for `record_success`:

1. `MATCH_LEARN` enabled (default on; `0`/`false`/`no`/`off` → no-op)
2. not `fetch_failed`
3. `offers_found >= 1`
4. `rewrite_heads_compatible(user, effective)` (+ residual `rewrite_compatible`)
5. score ≥ `min_score_to_learn` (default **0.50**)
6. alignment ok **or** (score ≥ τ and not reject)
7. `package_class_ok is not False` when caller enforces

## Negative learn (§3.3)

| Event | Action |
|-------|--------|
| zero kept offers (not fetch_failed) | `record_miss` |
| `wrong_item` + effective term | `record_miss` + `demote(remove=True)` that rewrite; never success |
| `wrong_item` item-only (API) | clear **all** learned rewrites for query (+ raw zset poison rows) |

## Deliverables

| Path | Role |
|------|------|
| `backend/app/services/rag/learn_policy.py` | single door: `on_search_item_result`, `on_user_feedback`, `MATCH_LEARN` |
| `backend/app/services/rag/store.py` | `demote()` primitive (zrem/hdel or negative zincrby) |
| `backend/app/services/llm/verifier.py` | funnels success/miss through learn_policy |
| `backend/app/api/routes/feedback.py` | `wrong_item` → `on_user_feedback` (API-level; Flutter payload is M6) |
| `backend/tests/test_learn_policy.py` | 3-S1…3-S8 coverage |

## Commands

```bash
cd backend
pytest tests/test_learn_policy.py tests/test_rag_agents.py tests/test_labeler.py \
  tests/test_outcome_log.py tests/test_intent_heads.py tests/test_relevance_quality.py \
  tests/test_ranking.py tests/test_feedback.py -q
```

## Grep (3-S1)

```text
app/cache.py                     → rag_store().record_success  (prewarm/legacy wrapper)
app/services/rag/learn_policy.py → only production door
app/services/rag/store.py        → primitives record_success / record_miss / demote
app/services/llm/verifier.py     → on_search_item_result only (no await rag.record_*)
```

## Out of scope (not done)

- M4 offline rescore / live smoke scripts
- M6 Flutter feedback field wire (API path + unit demote covered)
- Lexicon mining

## Git

```text
cf851c3 feat(match): Phase 3 learn_policy v2 (single door for RAG mutations)
5080229 test(match): API wrong_item demote + M3 report SHA
<tip>    fix(match): wrong_item clears all rewrites when term unknown
```

Primary feature: `cf851c3`. Tip SHA filled after commit/push.
