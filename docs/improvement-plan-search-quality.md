# Improvement plan — search usefulness (post phone eval 2026-07-18)

**Status:** draft plan (not yet executed)  
**Product lock:** Compre Barato Alagoas only  
**Trigger:** Physical-device install + live basket run scored **~3/10** for real shopping usefulness  
**North star metric:** *Would a Maceió shopper trust this screen enough to pick a store and leave?*

---

## 1. Problem statement

The pipeline **runs** (rewrite → SEFAZ/web → rank → savings UI), but **results often fail the trust test**:

| Failure mode | Evidence (this session) | User impact |
|--------------|-------------------------|-------------|
| **Wrong SKU** | “Óleo” → óleo de coco 15 ml sachets; “Ovo” → “MAC … OVOS” pasta | “Cheapest” is not the product they meant |
| **Partial basket sold as full win** | **4/10** items · **Faltam 6** + hero **Economize R$ 5,64** | Savings look decisive while 60% of list has no price |
| **Unit-price sort without package priors** | 15 ml coco wins on package price / weird unit_price | Tiny packs dominate cooking-oil intent |
| **Coverage fragility** | 10-staple `POST /api/v1/search` can **504** | Multi-item baskets unreliable under load |
| **No store catalog** | API is product-search only (by design today) | Cannot “list all latest unique items per store” |

We already have relevance rules (`rag/relevance.py` staples, noise) and Verifier min scores, but **live matches still leak** (abbreviations like `MAC`, coconut oil under `oleo`, single eggs vs dozen).

**Out of scope for this plan:** full store inventory export (SEFAZ client has no “all SKUs for CNPJ”); that remains a later data product if/when we own a NFC-e warehouse.

---

## 2. Goals & non-goals

### Goals (ordered)

1. **Intent-faithful matches** for top staples (óleo soja 900 ml-class, ovos bandeja/dúzia, açúcar 1 kg, arroz, feijão, leite, café, macarrão as pasta only when asked).
2. **Honest partial baskets** — never present partial coverage as a complete “economize X” without hard framing.
3. **Stable multi-item latency** — 8–15 staples complete within product SLA (target: p95 &lt; 45 s stream done; hard fail better than hang/504).
4. **Measurable quality** — regression suite + admin metrics so wrong-SKU cannot ship silent.

### Non-goals (now)

- Own complete per-store catalog dump API.
- Perfect semantic understanding of every regional brand name.
- iOS App Store ship (tracked separately in `TODO.md`).
- Replacing SEFAZ as source of truth.
- **Full UI viewport matrix / visual QA suite** (147-cell capture, multi-format VIDEO+PNG, A4–A7 visual fan-out).  
  **Operator (2026-07-18):** this milestone is **functionality-first**, not looks. Ship on match correctness, honest partial-basket behavior, backend/pytest, light Flutter unit tests, and targeted phone re-eval — **not** matrix green.
- **Thorough whole-app testing.** Do **not** treat this work as a reason to re-run full product e2e, residual matrix cells, or broad regression campaigns. **Only improve the known problem points** (wrong oil/egg matches, package-class ranking, overconfident partial savings, multi-item flakiness) and prove those fixes with **scoped** tests.

### Success criteria (exit when true)

| # | Criterion | How measured |
|---|-----------|--------------|
| S1 | Staple intent suite ≥ **90%** “acceptable top match” | Offline golden + CI pytest |
| S2 | Zero UI that shows savings **without** coverage fraction | Flutter unit/widget tests (no full matrix) |
| S3 | For oil/eggs/sugar fixture basket: **no** coco 15 ml / pasta-as-egg in top store lines | Fixture integration test |
| S4 | 10-item Maceió staple search p95 &lt; **45 s** on prod-like stack | Live/smoke timing |
| S5 | Phone re-eval usefulness score **≥ 7/10** (same rubric) | Human + agent checklist |

---

## 3. Workstreams

### W1 — Matching & ranking correctness (P0)

**Owner area:** `backend/app/services/rag/relevance.py`, `ranking.py`, `normalization/`, Verifier

| Work item | Detail |
|-----------|--------|
| W1.1 Package-class priors | For staples, prefer package sizes in grocery range (óleo ~500 ml–1 L; ovos 6/12/20/30; not 15 ml). Reject or heavily demote outliers (e.g. unit_price absurd vs peers, qty &lt; 50 ml for cooking oil). |
| W1.2 Noise expansions | Treat `MAC`/`MACARR` as pasta noise when intent is `ovo`/`ovos`; `coco` + small volume as off-intent for plain `óleo` unless query says coco. |
| W1.3 Intent dimension lock | `óleo` without “coco” → mass cooking oils only; `ovo` → egg products not pasta “c/ovos”. Encode as hard reject rules + tests. |
| W1.4 Best-offer key | Keep unit_price primary **among same package class**; add `package_class_score` then freshness. Do not crown 15 ml over 900 ml because package R$ is lower. |
| W1.5 Confidence on ItemOffer | Expose `match_score` (or band) to client; hide ultra-low confidence behind “incerto” or drop. |
| W1.6 Golden fixtures | Fixed NFC-e-like descriptions (coco 15 ml, MAC OVOS, ACUCAR 1KG, OLEO SOJA 900ML) → assert kept/rejected. |

**Done when:** S1 + S3 green in CI.

### W2 — Honest results UX (P0)

**Owner area:** Flutter search results, share savings, store cards

| Work item | Detail |
|-----------|--------|
| W2.1 Coverage-first hero | Hero copy only if coverage ≥ threshold (e.g. ≥ 70% **or** all items found). Else: “Encontramos 4 de 10 — compare só o que tem preço” (no “economize R$ X” as primary). |
| W2.2 Per-line product honesty | Always show NFC-e description under query; highlight when rewrite ≠ match class. |
| W2.3 Missing items panel | Explicit list of missing queries + “try refine” chips (use `suggested_refinements` / rewrites). |
| W2.4 Rank reason transparency | Surface `rank_reason` + coverage in store header (already partially there: “4 de 10”). |
| W2.5 Savings share gate | Disable or reword **Compartilhar economia** when partial or low confidence. |

**Done when:** S2 green; phone re-eval no longer “looks complete when incomplete.”

### W3 — Coverage & latency (P1)

**Owner area:** `search_service`, cache, SEFAZ/web concurrency, nginx timeouts

| Work item | Detail |
|-----------|--------|
| W3.1 Cache hit path | Confirm warm cache for top staples (prewarm job already exists — expand + monitor). |
| W3.2 Concurrency & timeouts | Align app `_searchTimeout`, backend SEFAZ, nginx `proxy_read_timeout` so multi-item never 504 after work is still useful; prefer partial final with `partial=false` + missing list. |
| W3.3 Progressive trust | Stream already exists — ensure final “done” never drops found items; show early partial with clear “buscando mais…”. |
| W3.4 Retry budget | Cap Verifier re-fetch so latency doesn’t explode; prefer better first search_term from RAG. |
| W3.5 Empty / thin radius | If radius 8 km thin, auto-suggest expand (settings already 1–15) once with user-visible note. |

**Done when:** S4 on live/staging.

### W4 — Quality measurement loop (P1)

| Work item | Detail |
|-----------|--------|
| W4.1 Staple eval harness | Script: N baskets × Maceió origin → JSON report (match rate, wrong-class rate, latency). |
| W4.2 Admin quality tab | Track wrong-class / low-score drop rates if not already; alert on regression. |
| W4.3 Phone checklist | Phase C: fixed 10-item list + screenshot rubric (usefulness 0–10) after each matching release. |
| W4.4 RAG learn guard | Only learn term mappings when package-class OK (raise `min_score_to_learn` + class check) so coco-oil doesn’t poison “óleo”. |

**Done when:** weekly eval number is visible; CI blocks known regressions.

### W5 — Data model / API evolution (P2 — after W1–W2)

| Work item | Detail |
|-----------|--------|
| W5.1 Response fields | `match_score`, `package_class`, `rejected_reason` (debug/admin), coverage on metrics. |
| W5.2 Optional multi-offer | Return top-3 candidates per item per store (schema already reserved `is_best_match`). |
| W5.3 Catalog research spike | Document whether SEFAZ or third parties ever support store-scoped dumps; **decision**: own NFC-e warehouse vs never. No build without spike memo. |
| W5.4 GTIN staples dictionary | Curated GTINs for top 30 staples → prefer GTIN search when known (higher precision). |

**Done when:** spike memo filed; multi-offer behind flag if shipped.

---

## 4. Phased delivery

```text
Phase A (1–2 days)   P0 trust: W1.1–W1.6 + W2.1–W2.5 + tests
Phase B (2–4 days)   P1 scale: W3.* + W4.*
Phase C (optional)   P2 API/data: W5.* after A+B show ≥7/10 on phone
```

Do **not** start W5 catalog work before match honesty ships — catalog dumps won’t fix wrong SKUs on basket search.

---

## 5. PR plan (incremental)

| PR | Title | Depends | Scope |
|----|-------|---------|--------|
| **PR1** | `fix(match): staple package-class filters + oil/egg fixtures` | — | relevance + ranking keys + pytest goldens (coco 15 ml, MAC OVOS reject; soja 900 ml keep) |
| **PR2** | `feat(api): match_score + package_class on ItemOffer` | PR1 | schema + populate from scorer; backward compatible |
| **PR3** | `feat(ui): honest partial-basket hero & savings gate` | PR2 optional | Flutter results + goldens; coverage-first copy |
| **PR4** | `fix(search): multi-item timeout/partial + prewarm staples` | PR1 | timeouts, prewarm list, stream finalization |
| **PR5** | `test(eval): staple basket harness + CI job` | PR1 | script + CI artifact; fail on wrong-class rate |
| **PR6** | `docs(spike): store catalog feasibility` | — | parallel OK; no product code required |

Ship order: **PR1 → PR3** is the minimum path to re-score phone usefulness. PR2 can merge with PR1 if small.

---

## 6. Key decisions (proposed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| D1 Ranking | Package class **before** raw unit_price for staples | Prevents 15 ml winning “óleo” |
| D2 Partial savings | **No** primary “economize R$” under coverage threshold | Stops overconfident hero |
| D3 Catalog API | **Not** in near-term roadmap | Upstream + cost; doesn’t fix match quality |
| D4 LLM on hot path | Keep Verifier deterministic; LLM only for parse/rewrite | Cost + latency; rules fix known failures first |
| D5 Learning | RAG only learns high-score **in-class** wins | Avoids poisoning cache |

Open for product: exact coverage threshold (propose **0.7** or “all items”); whether single-egg “OVOS UN” is acceptable when user types “ovo” (propose: demote vs bandeja/dúzia, allow if only option with low confidence badge).

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Stricter filters → more “missing” | Better empty UX (W2.3); refine chips; slightly wider search_term variants |
| SEFAZ/web still slow | Partial results + prewarm + concurrency caps |
| Overfit goldens | Keep fixtures diverse; monthly phone eval |
| Users liked big fake savings | Prefer trust over dopamine; A/B only after honesty baseline |

---

## 8. Acceptance re-eval rubric (phone)

Same as 2026-07-18 session, score 0–10:

1. Coverage of list  
2. Product relevance per line  
3. Price realism for intent  
4. Store comparison honesty  
5. Actionability (“I know where to go”)  
6. UI clarity  

**Ship bar for “matching quality” milestone:** mean ≥ **7**, and no line is an obvious wrong category (pasta-as-egg, sache-as-cooking-oil).

---

## 9. Immediate next action

1. Implement **PR1** (package-class + fixtures) — highest ROI, pure backend, tests.  
2. Land **PR3** honesty UI same week.  
3. Re-install APK / re-run the 10-item list on the lab phone; write score into `.grok/status/` if session open.

---

*Written after live phone eval + production API probe. Update this file when phases complete.*
