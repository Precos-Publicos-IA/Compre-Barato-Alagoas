# Implementation plan — self-improving product matching

**Status:** ready to execute (phased)  
**Product lock:** Compre Barato Alagoas only  
**Written:** 2026-07-23  
**Depends on:** head-aligned spine (`backend/app/services/rag/intent.py`), existing RAG store, honest eval harness, feedback API  
**Related:** `docs/improvement-plan-search-quality.md` (usefulness / package-class), `.grok/status/matching_reliability_plan.md`  
**North star:** Matching quality improves from production + eval evidence **without** per-SKU denylist patches; regressions are caught before ship.

---

## 0. Problem and principle

### Problem

Matching quality today improves only when agents add rules or run one-off evals. RAG can learn rewrites, but:

- There is no durable **search outcome log**
- There is little **negative** learning (wrong_item / weak tops)
- There is no **scheduled** lexicon/rewrite hygiene from data
- **Fetch failures** (~55s `items_fetch_failed`) are easily confused with **match** failures

### Principle

```text
Observe → Label (cheap first) → Learn (head-safe only) → Measure (CI + live) → Deploy
```

**Safety rail (non-negotiable):** learning and rewrites must pass head alignment (`intent.alignment_verdict` / `rewrite_heads_compatible`). Empty is better than wrong class. Never encode incident pairs as the primary fix.

**Separation of concerns:**

| Track | Metric | Owner area |
|-------|--------|------------|
| **Match quality** | among `stores > 0` and `items_fetch_failed = 0` | `rag/`, verifier, ranking |
| **Fetch reliability** | staple `items_fetch_failed` rate, p95 latency | SEFAZ client, prewarm, deadlines |

Do not grade matching quality on rows that never got SEFAZ data.

---

## 1. Goals and non-goals

### Goals

1. **Closed loop:** every (or sampled) live search can improve future rewrites/lexicon under hard safety rules.
2. **Automated regression:** property tests + goldens + offline rescore block silent quality loss.
3. **Actionable labels:** free structural labels first; user feedback second; expensive human/LLM last.
4. **Ship-safe learning:** no production learn path that can reintroduce egg-bleed or modifier pollution.
5. **Operable:** one primary eval command; clear post-deploy smoke; versioned match rules in metrics.

### Non-goals (this plan)

- Full private NFC-e warehouse / store catalog dump API
- LLM score on every candidate SKU
- Perfect coverage of all Brazilian grocery brands by hand
- Replacing head alignment with embeddings alone
- Full UI matrix as part of matching work (functionality-first)
- **Full `ui-viewport-qa` / multi-format visual e2e / A4–A7 ship path** for matching-loop PRs

### Verification policy (matching-loop work)

| Required | Not required |
|----------|----------------|
| Backend `pytest` (intent, relevance, labeler, learn_policy, outcome_log) | Full Flutter viewport matrix |
| API / function e2e: TestClient search + outcome log lines; scripts vs **local mock** SEFAZ | Puppeteer matrix capture |
| Serial **live** smoke scripts post-deploy only (CONCURRENCY=1) | Emulator/phone UI QA |
| Phase **definitions of success** in this doc | ui-viewport-qa A7 for matching commits |

If a PR touches Flutter feedback payload only: run the **minimal** related `flutter test`, not the full UI suite.

### Success criteria (exit when true)

| ID | Criterion | Measure |
|----|-----------|---------|
| S1 | Property suite green in CI on every backend change | `pytest tests/test_intent_heads.py` |
| S2 | Offline rescore of last labeled wrong tops ≥ prior baseline | script + artifact in CI or nightly |
| S3 | Learn path refuses head-incompatible + weak + fetch_failed | unit tests on learn policy |
| S4 | Search outcome log exists and is written for live searches (or sampled ≥10%) | ops check / unit with fake sink |
| S5 | Negative feedback demotes or blocks bad RAG mappings | integration test |
| S6 | Post-deploy serial smoke (≤15 queries) documented and runnable | one script + report path |
| S7 | Match vs fetch SLOs reported separately in overall eval | report template |

---

## 2. Current building blocks (do not rebuild)

| Component | Path | Role in loop |
|-----------|------|----------------|
| Head intent | `backend/app/services/rag/intent.py` | Structure + reject modifier pollution |
| Scoring | `backend/app/services/rag/relevance.py` | score + hard rejects + head gate |
| RAG store | `backend/app/services/rag/store.py` | rewrite learn/lookup |
| Verifier learn | `backend/app/services/llm/verifier.py` | calls `record_success` when offers kept |
| Metrics | `SearchMetrics` (`items_fetch_failed`, rewrites, match_rate) | observe |
| Feedback | `POST /api/v1/feedback` + Flutter feedback card | user labels |
| Eval | `backend/scripts/eval_shopping_list_100.py` | measure |
| Training log | `backend/data/training-datasets/alagoas_search_10k.jsonl` | bootstrap mining |
| Prewarm | `deploy/prewarm-staples.sh`, `scripts/prewarm_staples.py` | fetch track |
| Goldens | `backend/tests/test_relevance_quality.py`, `test_intent_heads.py` | CI floor |

---

## 3. Target architecture

```text
                    ┌──────────────────────────────┐
  Client search ──► │ search_service / stream       │
                    │  + match_rules_version        │
                    └───────────┬──────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
        SEFAZ fetch      score/rank/RAG      OutcomeLogger
        (fetch track)    (match track)       (JSONL / Redis stream / file)
                                │                 │
                                ▼                 ▼
                         record_success     Labeler (auto)
                         record_miss        │
                         record_feedback ◄──┘
                                │
                                ▼
                         RAG + optional lexicon
                                │
              nightly/CI ◄──────┴──────► offline rescore + live smoke
```

### New modules (proposed)

| Module | Responsibility |
|--------|----------------|
| `backend/app/services/rag/outcome_log.py` | Append structured search/item outcomes |
| `backend/app/services/rag/labeler.py` | `auto_label(query, description, context) → Label` |
| `backend/app/services/rag/learn_policy.py` | Central gate for success/miss/feedback → RAG mutations |
| `backend/scripts/mine_match_lexicon.py` | Heads/synonym candidates from logs + 10k |
| `backend/scripts/offline_rescore_match.py` | Rescore stored tops with current scorer |
| `backend/scripts/match_live_smoke.py` | Serial ≤15 query post-deploy smoke |
| `backend/data/matching/` | Versioned lexicon artifacts (generated + reviewed) |

Keep **fetch** improvements out of learn_policy except: never learn from `items_fetch_failed`.

---

## 4. Phases (implementation order)

Effort: **S** ≤1 day · **M** 2–4 days · **L** ≥1 week wall-clock for one worker

**How to read “Definition of success”:** each phase is **done only when every bullet under that phase’s definition is true**. “Done when” on tasks is the micro-check; the phase definition is the gate for starting the next phase.

### Phase success map (quick)

| Phase | One-line success |
|-------|------------------|
| **0** | Baseline metrics recorded + goldens green + `match_rules_version` visible on API |
| **1** | Live search can append privacy-safe outcome JSONL when env set; disabled by default path is no-op |
| **2** | `auto_label` is pure, tested, and used by the log (or ready to plug) with head-safe semantics |
| **3** | All RAG writes go through learn_policy; poison/weak/fetch_fail cannot success-learn; wrong_item demotes |
| **4** | Offline rescore + serial live smoke are one-command scripts with machine-readable artifacts |
| **5** | Miner produces versioned lexicon from data; loading it does not regress property/goldens |
| **6** | End-to-end: user “item errado” reaches learn_policy with query + description |
| **7** | Shadow/model scorer non-regresses offline + smoke before any default flip |
| **8** | Staple fetch_fail rate and p95 are measured post-deploy and improved vs baseline or hard-blocked with evidence |

---

### Phase 0 — Baseline freeze (S) — day 0

**Goal:** Know what “better” means before changing learn paths.

| Task | Detail | Done when |
|------|--------|-----------|
| 0.1 Snapshot metrics | Document tip SHA, last overall eval path, staple empty rate, soft quality notes | short note in plan appendix or session |
| 0.2 Freeze gold set | Ensure `test_intent_heads` property list + PR1–PR3 goldens run in CI (already part of pytest) | green CI on main |
| 0.3 Tag match rules version | Add constant `MATCH_RULES_VERSION = "2026-07-23-head-v1"` in `intent.py` or `relevance.py`; plumb into `SearchMetrics` (optional field) | response/metrics include version |

**Deliverable:** version string live; no behavior change required beyond metrics.

**PR:** `chore(match): expose match_rules_version for learning loop`

#### Definition of success — Phase 0

Phase 0 **succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 0-S1 | Baseline snapshot exists with **git SHA**, date, pointer to latest overall eval (e.g. `worker_w_eval_overall_report.md`), and raw **found_rate / fetch_fail_rate / p50–p95** if available | File under `.grok/status/` or appendix §14 filled |
| 0-S2 | `pytest tests/test_intent_heads.py tests/test_relevance_quality.py -q` is **green** on that SHA | Local + CI |
| 0-S3 | Constant `MATCH_RULES_VERSION` exists and is **stable string** (not empty) | Code search |
| 0-S4 | At least one search API response path exposes `match_rules_version` on **metrics** or response (documented field) | `curl`/TestClient asserts field present |
| 0-S5 | No intentional matching score behavior change in this phase (diff limited to version plumbing + docs) | Review diff |

**Phase 0 fails if:** version is only a code comment, or baseline snapshot is missing numbers/paths so later phases cannot claim “improved vs baseline.”

---

### Phase 1 — Observe: search outcome log (M) — days 1–3

**Goal:** Durable, privacy-safe records of what matching saw.

#### 1.1 Schema (item-level, one row per requested label)

```json
{
  "ts": "ISO-8601",
  "request_id": "...",
  "match_rules_version": "2026-07-23-head-v1",
  "query": "peito de frango",
  "intent_head": "peito",
  "intent_mods": ["frango"],
  "search_term": "peito frango",
  "data_source": "web",
  "items_fetch_failed": false,
  "latency_ms": 38000,
  "top_descriptions": ["SOPA VONO PEITO FRANGO...", "..."],
  "top_scores": [0.42, 0.40],
  "alignment_top": "ok|reject|unknown",
  "auto_label": "good|weak|bad|empty_fetch|empty_no_data|unknown",
  "stores_found": 5,
  "list_id": "optional",
  "analytics_id": "optional-hashed-only"
}
```

**Privacy:** no device tokens in clear text in long-lived logs; prefer analytics_id only if usage stats on; respect LGPD retention (align with existing search log TTL if any).

#### 1.2 Sink

| Env | Behavior |
|-----|----------|
| `MATCH_OUTCOME_LOG_PATH` | append JSONL (dev + simple VPS) |
| unset | no-op or sample 0% |
| later | Redis stream / object storage |

Sample rate: `MATCH_OUTCOME_LOG_SAMPLE` default `1.0` prod can set `0.1` if volume hurts.

#### 1.3 Wire points

- End of per-item path in `search_service` / catalog search after offers filtered (both code paths if dual)
- Include stream final and non-stream final
- **Do not** log full store lists forever if size is large — top 3 descriptions enough

#### 1.4 Tests

- Unit: logger writes expected keys; no-op when disabled
- No secrets in fixture logs

**PR:** `feat(match): structured search outcome log (sampled JSONL)`

#### Definition of success — Phase 1

Phase 1 **succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 1-S1 | Module `outcome_log.py` (or equivalent) exists with **append** + **no-op** modes | Code + unit tests |
| 1-S2 | With `MATCH_OUTCOME_LOG_PATH` set and sample rate 1.0, **one** `POST /api/v1/search` (TestClient or live) appends **≥1 valid JSON line** per requested item (or per search if documented aggregate — must be stated) | Manual/scripted check |
| 1-S3 | With path **unset**, search still **200** and **zero** log files created (no-op) | Test |
| 1-S4 | Each logged line includes at minimum: `ts`, `match_rules_version`, `query`, `items_fetch_failed`, `top_descriptions` (may be empty list), `stores_found` | Schema test |
| 1-S5 | Logged lines **never** contain raw `device_token` / `Authorization` / SEFAZ app token | Grep test on sample + code review |
| 1-S6 | Sample rate 0.0 produces **no** lines for N searches | Test |
| 1-S7 | `.env.example` documents `MATCH_OUTCOME_LOG_PATH` and `MATCH_OUTCOME_LOG_SAMPLE` | File present |
| 1-S8 | `pytest` green including new outcome_log tests | CI |

**Phase 1 fails if:** logging only works in a one-off script, not on the real search path; or full baskets dump unbounded store payloads; or secrets appear in JSONL.

**Maps to plan S4.**

---

### Phase 2 — Label: auto-labeler (S–M) — days 2–4 (overlap OK with late P1)

**Goal:** Cheap labels for every logged row.

#### 2.1 `auto_label` rules (priority order)

1. `items_fetch_failed` → **`empty_fetch`** (not a match label)
2. no stores / no descriptions → **`empty_no_data`**
3. `alignment_verdict(query, top_desc) == reject` → **`bad`**
4. existing hard-reject score floor (`score < 0.2`) → **`bad`**
5. score ≥ 0.5 and alignment ok and not noise → **`good`**
6. score mid or known weak patterns (optional heuristics: `SOPA`/`SALG`/`MOLHO` as top for non-sauce intent) → **`weak`**
7. else **`unknown`**

#### 2.2 API for reuse

```python
def auto_label(query: str, description: str | None, *, fetch_failed: bool, score: float | None) -> Label
```

Used by: outcome log, offline rescore, learn policy, eval reports.

#### 2.3 Tests

- Property: all `HEAD de MOD` vs query=MOD → `bad`
- Goldens from honest wrong_class tops → mostly `bad` under head gate
- fetch_failed → `empty_fetch` even if description leftover

**PR:** `feat(match): auto_label for outcomes (head-safe)`

#### Definition of success — Phase 2

Phase 2 **succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 2-S1 | `auto_label(...)` is a **pure function** (no I/O, no Redis) in `labeler.py` | Code review |
| 2-S2 | Label enum/set is fixed and documented: at least `good`, `weak`, `bad`, `empty_fetch`, `empty_no_data`, `unknown` | Docs + type |
| 2-S3 | **Priority order** in §2.1 is implemented: `fetch_failed=True` ⇒ always `empty_fetch` even if description is non-empty | Unit test |
| 2-S4 | Property: for ≥10 carriers × ≥3 mods, query=MOD and desc=`{CARRIER} DE {MOD}` ⇒ `bad` (or alignment reject path) | `test_intent_heads` or labeler tests |
| 2-S5 | Fixture: `queijo` + `PAO DE QUEIJO` ⇒ `bad`; `queijo` + `QUEIJO MUSSARELA` ⇒ not `bad` (good/weak/unknown OK) | Unit test |
| 2-S6 | Fixture: peito/ovos-style reject descriptions ⇒ `bad` | Unit test |
| 2-S7 | Outcome log **or** a single integration helper writes `auto_label` on each line when labeler is available | Integration or log schema test |
| 2-S8 | `pytest tests/test_labeler.py` (or equivalent) **green** in CI | CI |

**Phase 2 fails if:** labels require LLM; or `empty_fetch` is conflated with `bad`; or property pollution cases are not `bad`.

---

### Phase 3 — Learn policy v2 (M) — days 4–7

**Goal:** One door for all RAG mutations.

#### 3.1 Replace ad-hoc `record_success` call sites

Central API:

```python
learn_policy.on_search_item_result(...)
learn_policy.on_user_feedback(kind, query, description, list_id, ...)
```

#### 3.2 Positive learn (`record_success`) only if **all** hold

- not fetch_failed  
- at least one kept offer  
- `rewrite_heads_compatible(user, search_term)`  
- `alignment_verdict(user, best_description) == ok` (or score ≥ τ and not reject)  
- score ≥ `min_score_to_learn` (keep 0.50 from verifier D5)  
- package_class_ok if already enforced  

#### 3.3 Negative learn

| Event | Action |
|-------|--------|
| `wrong_item` feedback with description | `record_miss` + optional `zrem` / demote effective term; never `record_success` |
| auto_label `bad` on top with high prior rewrite | demote that rewrite for user_term |
| repeated weak tops for same rewrite | soft demote after N (config) |

#### 3.4 Explicit non-learns

- empty_fetch / empty_no_data  
- alignment reject  
- poisoned rewrites (already blocked)  

#### 3.5 Tests

- peito → ovos never stored  
- queijo → pao de queijo never stored  
- wrong_item demotes  
- fetch_failed does not success-learn  

**PR:** `feat(match): learn_policy v2 with negative feedback`

#### Definition of success — Phase 3

Phase 3 **succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 3-S1 | **No** direct `rag.record_success` from verifier/search outside `learn_policy` (primitives may exist; call sites funneled) | Grep call sites |
| 3-S2 | Positive learn **refuses** when `items_fetch_failed` / fetch_failed flag set | Unit test |
| 3-S3 | Positive learn **refuses** `user_term → effective` when `rewrite_heads_compatible` is false (peito→ovos, queijo→pão de queijo) | Unit test |
| 3-S4 | Positive learn **refuses** when best kept description has `alignment_verdict == reject` | Unit test |
| 3-S5 | Positive learn **refuses** when score &lt; `min_score_to_learn` (default 0.50) | Unit test |
| 3-S6 | Positive learn **accepts** a happy path (e.g. arroz → arroz tipo 1 with good description) and Redis/zset (or fake store) shows mapping | Integration test |
| 3-S7 | `on_user_feedback(kind=wrong_item, …)` **demotes or removes** mapping and **never** calls success | Unit/integration |
| 3-S8 | Env `MATCH_LEARN=0` (or equivalent) makes learn_policy a **no-op** for writes | Test |
| 3-S9 | `pytest` green including `test_learn_policy.py` | CI |

**Phase 3 fails if:** any production path still increments RAG success on head-incompatible rewrites; or wrong_item is log-only without learn effect when Redis available.

**Maps to plan S3, S5.**

---

### Phase 4 — Measure: offline rescore + live smoke (M) — days 5–8

**Goal:** Every scorer/learn change has a number before ship.

#### 4.1 Offline rescore script

Input: `match_eval_100_honest.json` tops and/or outcome log tops  
Output: `.grok/status/match_offline_rescore_<date>.json`

Report: counts `bad→empty`, `bad→still_bad`, `good→good`, `good→regressed`

#### 4.2 Live smoke script (serial)

Default 12–15 queries (staples + head incidents):  
`arroz, feijão, leite, óleo, ovo, banana, peito de frango, queijo, papel higiênico, sabão em pó, farinha de trigo, salsicha, alho, café, açúcar`

Flags: `--api`, `--out`, CONCURRENCY forced 1  
Classify each row: empty_fetch / empty_no_data / weak / good (via auto_label)

#### 4.3 CI policy

| Check | When |
|-------|------|
| pytest intent + relevance + learn_policy | every PR/push |
| offline rescore vs fixture tops | every PR if fixture committed; else nightly |
| live smoke | post-deploy only (not every unit test) |

**PR:** `test(match): offline rescore + live smoke scripts`

#### Definition of success — Phase 4

Phase 4 **succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 4-S1 | `offline_rescore_match.py` runs against a **committed fixture** (honest tops or subset) and exits 0 | `python scripts/offline_rescore_match.py --help` + dry run |
| 4-S2 | Offline artifact includes counts: at least `n`, `still_bad`, `now_empty_or_reject`, `regressed_good_to_bad` (names may vary; must be documented) | JSON schema in script README |
| 4-S3 | Offline rescore on pre-head **wrong_class** tops shows **0 regressed goods** vs empty/reject improvement for known poison pairs (or documented residual list ≤ agreed bound) | Artifact + short markdown |
| 4-S4 | `match_live_smoke.py` forces **concurrency 1**, default query list ≥12, writes JSON + optional md summary | Run against mock API or prod |
| 4-S5 | Live smoke summary reports **separately**: `fetch_fail_rate`, `found_rate`, `good_top_rate` / `weak_top_rate` among found | Output fields |
| 4-S6 | Live smoke is **not** required in default unit CI; docs state **post-deploy only** | CI yaml + docs |
| 4-S7 | One-line runbooks exist in script `--help` or `backend/data/matching/README.md` | Docs |
| 4-S8 | Backend pytest still green | CI |

**Phase 4 fails if:** scripts only exist as notebook/ad-hoc notes; or live smoke is wedged into every push CI and flakes on SEFAZ; or reports mix fetch empties into “bad match” without split.

**Maps to plan S2, S6, S7.**

---

### Phase 5 — Lexicon mining (M) — days 8–12

**Goal:** Structure knowledge grows from data, not tickets.

#### 5.1 Mine heads

From 10k JSONL + outcome log:

- Frequent first content tokens in **good** descriptions  
- Frequent user intent heads  

Write `backend/data/matching/heads_lexicon.vN.json` (generated).

#### 5.2 Mine synonym candidates

Pairs with high co-success and head compatibility; **never** auto-add cross-head pairs.  
Human or strict threshold promote into `_SYN_GROUPS` / data file.

#### 5.3 Load path

`intent.py` optionally loads external lexicon for head-candidate hints (brand-skip lists, known heads). Default empty = current behavior.

#### 5.4 Job

- `scripts/mine_match_lexicon.py`  
- Nightly or manual; CI runs miner on fixture sample in dry-run  

**PR:** `feat(match): lexicon mining from outcomes + 10k`

#### Definition of success — Phase 5

Phase 5 **succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 5-S1 | `mine_match_lexicon.py` produces a **versioned** JSON under `backend/data/matching/` with schema documented (e.g. `heads: [...]`, `generated_at`, `source`) | Run on 10k or fixture |
| 5-S2 | Dry-run on CI fixture completes in **&lt; 60s** and is non-flaky | CI job or local |
| 5-S3 | Miner **never** emits cross-head synonym pairs that fail `heads_compatible` (e.g. queijo↔pao) | Unit test on filter |
| 5-S4 | Loading lexicon is **opt-in** (env or file presence); default behavior = current intent without file | Test both modes |
| 5-S5 | With lexicon loaded, `pytest tests/test_intent_heads.py tests/test_relevance_quality.py` remains **green** | CI |
| 5-S6 | Promotion path documented: raw miner output ≠ auto-merge into code without review for synonyms | README |
| 5-S7 | At least one mined head list contains common staples (`arroz`, `feijao`, `leite`, …) when run on 10k | Spot check |

**Phase 5 fails if:** synonyms auto-merge into production without filter; or lexicon load breaks head pollution property tests.

---

### Phase 6 — Product feedback wire-through (S–M) — days 10–14

**Goal:** User “item errado” actually updates learn_policy.

| Task | Detail |
|------|--------|
| 6.1 Backend | feedback handler calls `learn_policy.on_user_feedback` with query + description when present |
| 6.2 Flutter | ensure wrong_item payload includes selected line description + original query (if not already) |
| 6.3 Admin (optional) | simple count of bad labels / week |

**PR:** `feat(match): wire wrong_item feedback into learn_policy`

#### Definition of success — Phase 6

Phase 6 **succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 6-S1 | API `wrong_item` (or equivalent) accepts **query** + **description** (or item text) fields; validated in OpenAPI/tests | TestClient |
| 6-S2 | Handler invokes `learn_policy.on_user_feedback` when those fields present | Unit/mock |
| 6-S3 | Flutter “Reportar item errado” sends **non-empty description** of the offending line and the **user query/label** | Widget/API contract test or manual script + Charles-level assert |
| 6-S4 | Integration: seed RAG success mapping → post wrong_item → mapping **demoted/absent** on lookup | Redis test |
| 6-S5 | Feedback still **200** and does not 500 if learn Redis is down (best-effort learn; feedback stored) | Test |
| 6-S6 | No device token written into outcome log from this path beyond existing privacy rules | Review |

**Phase 6 fails if:** UI only posts “wrong_item” without description/query so learn cannot act; or feedback hard-depends on Redis.

**Optional 6.3** is **not** required for phase success; if shipped, success = admin shows count ≥0 without error.

---

### Phase 7 — Optional scorer upgrade (L) — only after P1–P4 stable

**Goal:** Data-driven score among **head-ok** candidates only.

1. Export features from outcome log (head match, mod overlap, package class, score_rule, position)  
2. Train logistic/GBT offline; shadow-score in metrics  
3. Replace or blend with `score_description` behind flag `MATCH_SCORER=rules|shadow|model`  
4. Require offline rescore non-regression + live smoke  

**Do not start Phase 7** until outcome log has meaningful volume and learn_policy v2 is in prod ≥1 week.

#### Definition of success — Phase 7

**Entry criteria (must be true before work counts as Phase 7):**

| # | Entry criterion |
|---|-----------------|
| 7-E1 | Phases 1–4 **success** definitions met on production |
| 7-E2 | Outcome log has **≥ N labeled rows** (suggest N≥5000 item-rows or 14 days sampling—pick one and document) |
| 7-E3 | learn_policy v2 enabled in prod **≥7 days** without emergency `MATCH_LEARN=0` |

**Phase 7 succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 7-S1 | Feature export script produces training table from logs | Runbook |
| 7-S2 | `MATCH_SCORER=shadow` computes model score **without** changing ranking | Metrics/log compare |
| 7-S3 | Offline rescore: model/shadow **does not increase** `regressed_good_to_bad` vs rules baseline on frozen fixture | Artifact |
| 7-S4 | Offline: among head-ok candidates, model **improves** weak→good or reduces wrong tops on held-out set by agreed δ (document δ, e.g. +5% good_top or −20% bad_top) | Artifact |
| 7-S5 | Live smoke under shadow shows no fetch regression (fetch track unchanged) | Smoke JSON |
| 7-S6 | Default remains `rules` until explicit flip PR with 7-S3–7-S5 attached | Config |
| 7-S7 | Flip to `model` only with rollback flag and documented owner | Ops note |

**Phase 7 fails if:** model ranks head-reject candidates above floor; or default flips without offline gate.

---

### Phase 8 — Fetch track (parallel, not optional for user trust) (M)

Matching loop cannot look good if staples empty.

| Task | Status / plan |
|------|----------------|
| Prewarm on deploy | Started (`9ec6775`) — verify post-deploy warm p50 |
| Separate SLO dashboard | smoke script reports `fetch_failed_rate` vs `weak_rate` |
| Deadline / concurrency tuning | only with serial evidence, no stampede |
| UI honesty | fetch_failed copy shipped — keep |

Treat as **parallel workstream**, same repo, separate PRs from learn_policy.

#### Definition of success — Phase 8

Use **baseline** from Phase 0 snapshot / `worker_w_eval_overall_report.md` (2026-07-23 era: multi-query ~55s fetch fails on several staples).

Phase 8 **succeeds** when **all** of the following are true:

| # | Success criterion | How to verify |
|---|-------------------|---------------|
| 8-S1 | Post-deploy prewarm job **runs** (log line or script exit 0 on VPS/CI deploy path) | Deploy logs |
| 8-S2 | Serial smoke on **warm** path: ≥ **80%** of staple subset `{arroz, feijão, leite, óleo, ovo, café, açúcar}` returns `stores>0` **or** hard-block evidence that SEFAZ upstream is down (not our bug) | `match_live_smoke` JSON |
| 8-S3 | Among those staples that return 200 with data, **median latency ≤ 5s** on warm probe (cold may still be high) | Smoke latency field |
| 8-S4 | `fetch_fail_rate` on the 15-query smoke is **reported separately** from `weak_top_rate` | Report template |
| 8-S5 | Empty fetch continues to surface **honest** UI/API (`items_fetch_failed` / labels) — no silent “produto não existe” for timeout | Existing product tests + spot check |
| 8-S6 | No parallel stampede in smoke or prewarm (batch size 1 or documented safe concurrency) | Script flags / deploy script |

**Phase 8 fails if:** prewarm is code-only and never invoked after deploy; or success is claimed while staple fetch_fail remains ~same as baseline without upstream hard-block note.

**Note:** Phase 8 success is **not** required to finish matching MVP (P0–P4), but **is** required before marketing “reliable shopping lists.”

---

## 5. PR / ship map (recommended sequence)

```text
PR0  match_rules_version                    [S]
PR1  outcome_log + sample env               [M]
PR2  auto_label + tests                     [S]
PR3  learn_policy v2 + verifier/cache wire  [M]
PR4  offline_rescore + live_smoke scripts   [M]
PR5  feedback → learn_policy                [S]
PR6  lexicon miner + optional load          [M]
PR7  (optional) model scorer shadow         [L]
PRf  fetch/prewarm verification             [M, parallel]
```

Each PR: pytest green; no denylist-of-pairs; update this plan status line when merged.

Commit style (repo convention): direct to `main` after verification; no PR theater unless you change process.

---

## 6. File-level checklist

### Create

- [ ] `backend/app/services/rag/outcome_log.py`
- [ ] `backend/app/services/rag/labeler.py`
- [ ] `backend/app/services/rag/learn_policy.py`
- [ ] `backend/scripts/offline_rescore_match.py`
- [ ] `backend/scripts/match_live_smoke.py`
- [ ] `backend/scripts/mine_match_lexicon.py`
- [ ] `backend/tests/test_outcome_log.py`
- [ ] `backend/tests/test_labeler.py`
- [ ] `backend/tests/test_learn_policy.py`
- [ ] `backend/data/matching/README.md`
- [ ] `docs/self-improving-matching-plan.md` (this file)

### Modify

- [ ] `backend/app/schemas/search.py` — optional `match_rules_version`
- [ ] `backend/app/services/search_service.py` (+ catalog search if separate path) — log outcomes
- [ ] `backend/app/services/llm/verifier.py` — learn_policy only
- [ ] `backend/app/services/rag/store.py` — keep primitives; policy sits above
- [ ] `backend/app/api/routes/*feedback*` — negative learn
- [ ] `frontend` feedback payload if missing description/query
- [ ] `.env.example` — `MATCH_OUTCOME_LOG_*`, sample rate
- [ ] `deploy/` — ensure log dir writable if file sink on VPS

### Do not modify for this plan

- Per-product reject tables as primary mechanism  
- Parallel eval stampede scripts as quality ground truth  

---

## 7. Testing strategy

| Layer | What |
|-------|------|
| Unit | labeler, learn_policy gates, outcome_log format |
| Property | modifier pollution (existing + extend) |
| Golden | PR1–PR3 relevance fixtures |
| Integration | feedback → redis demotion (fakeredis or real test redis) |
| Offline | rescore honest tops artifact |
| Live | serial smoke post-deploy only |
| Full 100 | weekly / pre-release, CONCURRENCY=1 |

---

## 8. Rollout and ops

1. Deploy PR0–PR2 with log sampling **on** staging/prod path (disk volume check).  
2. Deploy PR3 learn_policy behind default **on** (safe by construction); monitor RAG key growth.  
3. After 48h, run offline rescore + live smoke; file overall eval.  
4. Enable PR5 feedback wire.  
5. Run miner; review synonym candidates before merging into code.  
6. Only then consider Phase 7.

**Rollback:** set learn to no-op env `MATCH_LEARN=0`; keep scoring/head gate; logs can stay.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Log volume / disk | sample rate; top-3 only; rotation |
| Learning wrong “goods” | head gate + min score + weak filter |
| Confusing fetch with match | separate labels and SLOs |
| Privacy | no tokens; retention aligned with existing analytics |
| Overfitting to 10k static set | prefer live outcome log over time |
| CI flaky live SEFAZ | never put live smoke in unit CI |

---

## 10. Suggested ownership of first execution slice

**MVP slice (ship in one coherent pass, ~1 week one worker):**

1. Phase 0 version  
2. Phase 1 outcome log  
3. Phase 2 auto_label  
4. Phase 3 learn_policy v2 (success + wrong_item)  
5. Phase 4 scripts (offline + live smoke)  

That alone is a **self-improving cycle** for rewrites + measurable quality, with head safety.

Lexicon mining and model scorer are **amplifiers**, not the MVP.

#### Definition of success — MVP slice

MVP is **successful** only when:

| # | Criterion |
|---|-----------|
| MVP-S1 | Phase **0** definition of success met |
| MVP-S2 | Phase **1** definition of success met |
| MVP-S3 | Phase **2** definition of success met |
| MVP-S4 | Phase **3** definition of success met (including wrong_item demote tests even if Flutter wire is partial) |
| MVP-S5 | Phase **4** definition of success met |
| MVP-S6 | All of the above are on `main` and **deployed** (or deploy hard-blocked with evidence) |
| MVP-S7 | Appendix records **SHAs** for each phase PR/commit |

Phase **6** (full Flutter wire) is **MVP-plus** if 3-S7 is satisfied via API tests only; full E2E UI wire still required for plan “executed-mvp+feedback”.

---

## 11. Definition of done for the whole plan

- [ ] MVP slice success (**MVP-S1–S7**)  
- [ ] Phase **6** definition of success (feedback UI → learn)  
- [ ] Phase **5** definition of success (lexicon) **or** explicitly deferred with reason  
- [ ] Phase **8** definition of success **or** upstream SEFAZ hard-block documented  
- [ ] Live smoke shows fetch vs weak vs good rates (4-S5)  
- [ ] Offline rescore of pre-head wrong_class tops remains emptied (no regression) (4-S3)  
- [ ] At least one controlled wrong_item demotion test green (3-S7 / 6-S4)  
- [ ] This plan marked **executed-mvp** (or **executed-full**) with SHAs in appendix §14  

---

## 12. Appendix — metric definitions

| Name | Definition |
|------|------------|
| **found_rate** | fraction probes with `stores > 0` |
| **fetch_fail_rate** | fraction with `items_fetch_failed > 0` |
| **good_top_rate** | among found, auto_label == good |
| **weak_top_rate** | among found, auto_label == weak |
| **bad_top_rate** | among found, auto_label == bad |
| **p50/p95 latency** | search wall time ms |

Report always split: **all probes** vs **found-only quality**.

---

## 13. Appendix — open questions (resolve during MVP if blocking)

1. VPS disk path for JSONL vs ship logs only to existing logging stack?  
2. Sample rate default prod 100% vs 10%?  
3. Should `weak` tops ever learn (no is default)?  
4. Retention days for outcome log (suggest 30–90)?  

---

---

## 14. Appendix — Phase 0 baseline (freeze)

| Field | Value |
|-------|--------|
| **Date (UTC)** | 2026-07-23 |
| **Baseline tip SHA** | `bc5964f` (`bc5964f46b96b2b492b9c9ef7dc9683f83c2cd0c`) |
| **MATCH_RULES_VERSION** | `2026-07-23-head-v1` |
| **Overall eval** | `.grok/status/worker_w_eval_overall_report.md` — **C+** |
| **found_rate** | 14/19 = **73.7%** |
| **fetch_fail_rate** | 4/18 singles (feijão, óleo, café, açúcar) |
| **p50 / p95 latency** | **~36595 / ~55715 ms** |
| **Snapshot note** | `.grok/status/match_baseline_phase0.md` |

Phase ship SHAs (filled as phases land):

| Phase | SHA | Notes |
|-------|-----|-------|
| 0+1 (M0/M1) | *(set on commit)* | version plumbing + outcome log |
| 2 | | auto_label |
| 3 | | learn_policy |
| 4 | | offline rescore + live smoke |

*End of plan. Execute MVP slice first; do not skip head safety for faster learning.*
