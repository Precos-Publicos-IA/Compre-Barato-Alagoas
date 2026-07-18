# F BLOCKED_429 — honest 100 live re-eval

**Status:** hard-blocked on production daily search quota  
**Worker:** `W-eval-honest`  
**Recorded (UTC):** 2026-07-18T15:52:39.869852+00:00

## Probe evidence (single call — did not burn 100)

| Field | Value |
|-------|-------|
| API | `https://alagoas.precospublicos.ia.br` |
| Query | `arroz` |
| HTTP | **429** |
| Latency ms | 642 |
| Error / body | `HTTP 429: {"detail":"Limite diário de buscas atingido. Tente novamente amanhã."}` |
| data_source | None |
| stores_found | None |
| found | False |

Production response (expected):

```text
{"detail":"Limite diário de buscas atingido. Tente novamente amanhã."}
```

## Why we stop

Prior invalid eval (`f7ef373`) used parallel load and poisoned empty-cache. Full honest
serial 100 would burn the remaining quota for no usable coverage while 429 is active.
**Do not** re-run the full 100 until a single staple probe returns HTTP 200 with stores.

## Script ready

Honest methodology is implemented in `backend/scripts/eval_shopping_list_100.py`:

- default `CONCURRENCY=1` (hard cap 2)
- one retry on empty stores / match_rate=0 after backoff
- verdicts: `pass` | `wrong_class` | `missing_after_retry` | `upstream_error`
- flushed progress, JSON + human report

## Re-run tomorrow (or when quota resets)

```bash
# 1) Probe first
python3 backend/scripts/eval_shopping_list_100.py --probe-only

# 2) If probe is 200 with stores for arroz (or any staple), full serial 100:
API_BASE=https://alagoas.precospublicos.ia.br CONCURRENCY=1 \
  python3 backend/scripts/eval_shopping_list_100.py \
  --out .grok/status/match_eval_100_honest.json
```

Exit codes:

- probe `--probe-only`: **0** if ok for full eval; **2** if 429/blocked; **1** other failure
- full eval: **0** always writes report (inspect `upstream_error` count)

## Related

- Catalog fixture: `backend/tests/fixtures/shopping_list_100.json` (A DONE)
- Match relevance fixes: `5853031` (C DONE)
- Empty-cache poison fix: task E (parallel worker)
