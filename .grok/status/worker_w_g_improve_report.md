# W-G-improve report — honest wrong_class match fix

**Status:** **G DONE**  
**Worker:** W-G-improve  
**Date:** 2026-07-18  
**Product SHA:** **`efca61d`** (`fix(match): block RAG cross-class rewrites causing egg/class bleed`)  
**Evidence in:** `.grok/status/match_eval_100_honest.json` (pass=71, wrong_class=20, missing_after_retry=9, found=91, all web)

## Root cause (not scorer alone)

Prior P0 egg hard-reject scored correctly **when** `search_term == label`. Live probes showed **RAG rewrite poison**:

| Query (examples) | Live `search_rewrites` | Top line |
|------------------|------------------------|----------|
| peito de frango, farinha, queijo, pão, água, molho, … | → **`ovos`** | OVOS BRANCOS UND |
| salsicha, salgadinho | → **`sal`** | Pipoca Bokus sal |
| sabão em pó | → **`leite`** | COCADA LEITE |
| papel higiênico | → **`papel toalha`** | PAPEL TOALHA MALU |

`score_description(label, "ovos", egg)` used intent `"peito de frango ovos"` → `_is_egg_intent` true → eggs kept (0.62). Poison was learned into Redis `rag:effective_for:*` after earlier wrong keeps / weak similar-term overlap (stopword **de**, sal⊂salsicha).

Empty is better than wrong class; 9 true `missing_after_retry` remain SEFAZ data gaps (not invented).

## Fixes shipped

| Area | Change |
|------|--------|
| `rag/store.py` | `rewrite_compatible` / `filter_compatible_terms`; refuse cross-class `record_success`; filter lookup + similar; content tokens (stopwords, min len 3); class conflicts (egg, higiênico/toalha, salsicha/sal, sabão/leite) |
| `rag/relevance.py` | Neutralize incompatible `search_term`; label-primary egg (and residual) hard rejects; papel toalha reject; salsicha/salgadinho/sabão primary-token gates |
| `llm/requester.py` + `verifier.py` | Only apply rewrite-compatible RAG alts/retries |
| tests | Goldens from honest WC NFC-e lines + RAG poison refusal |

## Tests

```text
pytest tests/test_relevance_quality.py tests/test_ranking.py tests/test_rag_agents.py  → green
pytest -q (full backend) → green
```

## Offline re-score (20 wrong_class, stored top_lines + observed poison terms)

| Outcome | Count |
|---------|------:|
| Class trap fixed → **empty** (no wrong top) | **20** |
| Residual wrong_class in fixture set | **0** |

Artifact: `.grok/status/match_eval_100_offline_rescore_g.json`

## Out of scope (task)

- Full 100 live re-eval (quota)
- Inventing SEFAZ coverage for 9 `missing_after_retry` (sal, bolacha, cerveja, achocolatado, detergente, amaciante, desinfetante, sabonete, shampoo)
- Parallel stampede

## Note for ops / H ship

Poison keys may still sit in production Redis; lookup **filters** them so they no longer apply. Optional: flush `rag:effective_for:*` / `rag:user_to_term:*` after deploy for cleanliness. Cache of raw SEFAZ rows is fine — relevance re-filters on each request.

## Acceptance

| Criterion | Status |
|-----------|--------|
| wrong_class themes fixed (egg bleed, papel, salsicha, sabão) | **YES** |
| pytest relevance/ranking + new goldens green | **YES** |
| Commit + push product fix | **YES** (see SHA below / session) |
| Report this file | **YES** |
| No SEFAZ invent for true missing | **YES** |
