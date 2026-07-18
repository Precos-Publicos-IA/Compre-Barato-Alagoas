# W-F-run / W-eval-honest — F honest serial 100 live re-eval

**Status:** **F DONE**  
**Worker:** W-F-run  
**Recorded (UTC):** 2026-07-18T16:28:44Z  
**API:** `https://alagoas.precospublicos.ia.br`  
**Method:** `CONCURRENCY=1` · one empty-retry · verdicts `pass | wrong_class | missing_after_retry | upstream_error`  
**Artifacts:**
- `.grok/status/match_eval_100_honest.json`
- `.grok/status/match_eval_100_honest_report.md`
- `.grok/status/match_eval_100_honest_run.log`

## Unblock path (before full run)

1. `--probe-only` initially: HTTP **200**, `data_source=sefaz`, **0 stores** (not 429) — not OK for full eval.
2. Root cause: official SEFAZ API path could “succeed” with empty `conteudo` and never fall back to Economiza website; local web scrape still returned arroz rows. E (`67c26ca`) was on main but analytics kwargs blocked later deploys.
3. Shipped `197628c` — empty official API → web fallback; `Analytics.record_search` accepts E honesty labels.
4. Deploy CI **29651426298** success; re-probe: **HTTP 200**, `data_source=web`, **stores=5**, top=`ARROZ EMOCOES INTEGRAL 1KG`, `ok_for_full_eval=true`.

## Summary table (honest 100)

| Verdict | Count |
|---------|------:|
| **pass** | **71** |
| **wrong_class** | **20** |
| **missing_after_retry** | **9** |
| **upstream_error** | **0** |
| total | 100 |
| found_count (any store hit) | 91 |
| retried_count | 9 |

### Latency (ms)

| | |
|--|--:|
| p50 | 11262 |
| p95 | 22986 |
| min / max | 198 / 24374 |
| mean | 7852 |

### data_source

| source | n |
|--------|--:|
| **web** | **100** |

## Coverage proof (≠ zero)

| Query | stores | found | verdict | top description |
|-------|-------:|:-----:|---------|-----------------|
| **arroz** | **5** | true | **pass** | ARROZ EMOCOES INTEGRAL 1KG |
| feijão | 5 | true | pass | FEIJAO PT T1 1KG OF3 |
| óleo | 5 | true | pass | OLEO DE SOJA SOYA 900ML |
| ovo | 5 | true | pass | OVOS EXTRA STA MARIA LUNA UN |

**Conclusion:** Prior “71 missing SEFAZ” from parallel stampede is **INVALID**. Serial web path finds rows for staples; missing_after_retry is **9/100**, not ~70%.

## missing_after_retry (9)

`sal`, `bolacha`, `cerveja`, `achocolatado`, `detergente`, `amaciante`, `desinfetante`, `sabonete`, `shampoo`

## wrong_class themes (20) — next match-improve backlog

Dominant signal: **egg cross-query bleed** — many non-egg queries ranked `OVOS BRANCOS UND` (farinha, queijo, pão, molho de tomate, peito de frango, …). Also generic intent misses (`salsicha`→pipoca, `salgadinho`→pipoca, `papel higiênico`→papel toalha, `sabão em pó`→cocada leite).

## By category (pass / wrong / missing / err)

| category | total | pass | wrong_class | missing | upstream |
|----------|------:|-----:|------------:|--------:|---------:|
| staples | 12 | 9 | 2 | 1 | 0 |
| dairy | 12 | 10 | 2 | 0 | 0 |
| oils | 12 | 10 | 2 | 0 | 0 |
| meat | 12 | 10 | 2 | 0 | 0 |
| produce | 12 | 12 | 0 | 0 | 0 |
| bakery | 8 | 3 | 4 | 1 | 0 |
| beverages | 10 | 6 | 2 | 2 | 0 |
| snacks | 6 | 4 | 2 | 0 | 0 |
| cleaning | 8 | 2 | 3 | 3 | 0 |
| hygiene | 6 | 3 | 1 | 2 | 0 |
| baby | 1 | 1 | 0 | 0 | 0 |
| pet | 1 | 1 | 0 | 0 | 0 |

## Next focus (not F)

- Match-improve: kill egg bleed + bread/cheese intent gates (wrong_class pile).
- Optional: investigate 9 true missings (cleaning/hygiene/beer) vs SEFAZ web gaps.
