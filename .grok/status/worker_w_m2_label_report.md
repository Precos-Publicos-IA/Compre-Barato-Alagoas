# W-m2-label — Phase 2 auto_label success map

| Field | Value |
|-------|--------|
| **Worker** | W-m2-label |
| **When (UTC)** | 2026-07-23 |
| **Plan** | `docs/self-improving-matching-plan.md` Phase 2 |
| **Testing policy** | Backend/function first — pytest only; no UI matrix |
| **Prior** | M0+M1 `5a16961` / tip was `4274a20` |

## Phase 2 — Definition of success

| ID | Criterion | Result | Evidence |
|----|-----------|:------:|----------|
| **2-S1** | `auto_label(...)` is a **pure function** (no I/O, no Redis) in `labeler.py` | **PASS** | `backend/app/services/rag/labeler.py`; `test_auto_label_is_pure_no_io_signature` |
| **2-S2** | Label set fixed: `good`, `weak`, `bad`, `empty_fetch`, `empty_no_data`, `unknown` | **PASS** | `Label` Literal + `LABELS` frozenset; module docstring; `test_label_set_documented_and_fixed` |
| **2-S3** | Priority: `fetch_failed=True` ⇒ always `empty_fetch` even with non-empty description | **PASS** | `test_fetch_failed_always_empty_fetch_even_with_description` |
| **2-S4** | Property: ≥10 carriers × ≥3 mods, query=MOD + `{CARRIER} DE {MOD}` ⇒ `bad` | **PASS** | `test_property_mod_alone_labels_carrier_de_mod_bad` (13 carriers × 5 mods) |
| **2-S5** | `queijo`+`PAO DE QUEIJO`⇒`bad`; `queijo`+`QUEIJO MUSSARELA`⇒ not `bad` | **PASS** | `test_queijo_pao_de_queijo_bad`, `test_queijo_mussarela_not_bad` |
| **2-S6** | peito/ovos-style reject descriptions ⇒ `bad` | **PASS** | pastel + egg SKU tests; SOPA weak-noise covered as non-good |
| **2-S7** | Outcome log writes real `auto_label` on each line | **PASS** | `build_item_outcome` calls `compute_auto_label`; `test_build_item_outcome_writes_real_auto_label`, `test_log_search_item_outcomes_persists_auto_label` |
| **2-S8** | `pytest tests/test_labeler.py` green | **PASS** | green with outcome_log + intent_heads + relevance_quality |

**Phase 2: PASS**

## Priority rules implemented (§2.1)

1. `fetch_failed` → `empty_fetch`
2. no description **or** `stores_found <= 0` → `empty_no_data`
3. `alignment_verdict == reject` → `bad`
4. `score < 0.2` → `bad`
5. `score ≥ 0.5` and alignment `ok` and not weak-noise → `good`
6. weak-noise tops (SOPA/SALG/MOLHO/…) or mid score or high+`unknown` align → `weak`
7. else → `unknown`

## Deliverables

| Path | Role |
|------|------|
| `backend/app/services/rag/labeler.py` | pure `auto_label` + `label_for_outcome` |
| `backend/app/services/rag/outcome_log.py` | wires real auto_label (no more `"unknown"` placeholder default) |
| `backend/tests/test_labeler.py` | 2-S1…2-S8 coverage |

## Commands

```bash
cd backend
pytest tests/test_labeler.py tests/test_outcome_log.py tests/test_intent_heads.py tests/test_relevance_quality.py -q
```

## Out of scope (not done)

- M3 learn_policy
- M4 offline rescore / live smoke scripts
- Flutter

## Git

```text
(see commit after push)
```
