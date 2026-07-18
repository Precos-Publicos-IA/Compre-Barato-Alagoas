# Worker W-eval-honest report

**Task:** F — honest 100 live re-eval  
**Status:** **BLOCKED_429** (script ready; full 100 not run)  
**Date (UTC):** 2026-07-18  
**Worker:** W-eval-honest

## Delivered

### 1. Script upgrade — `backend/scripts/eval_shopping_list_100.py`

Honest methodology (replaces invalid parallel defaults of prior `f7ef373` eval):

| Change | Detail |
|--------|--------|
| Default concurrency | **1** (env `CONCURRENCY`; hard cap **2**) |
| Empty / zero-match retry | **One** retry after backoff default **3s** (band 2–5s; `RETRY_BACKOFF_S`) |
| Verdicts | `pass` \| `wrong_class` \| `missing_after_retry` \| `upstream_error` |
| Upstream | HTTP **429** / **5xx** / non-200 / timeout → `upstream_error` (not “missing”) |
| Fields | `data_source`, latency (total + per-attempt), `top_lines`, `retried`, `retry_reason`, `attempts` |
| Progress | line-buffered `flush=True`; partial checkpoint every 5 |
| Outputs | JSON (`--out`) + human markdown report (`--report` or `*_report.md`) |
| Probe | `--probe-only` single staple call; exit **2** on 429, **0** if OK for full run |

Default out paths now point at honest artifacts:

- `.grok/status/match_eval_100_honest.json`
- `.grok/status/match_eval_100_honest_report.md`

### 2. Production probe (did **not** burn 100)

| | |
|--|--|
| API | `https://alagoas.precospublicos.ia.br` |
| Query | `arroz` |
| HTTP | **429** |
| Body | `Limite diário de buscas atingido. Tente novamente amanhã.` |
| Script exit | **2** via `--probe-only` |

Evidence file: [`.grok/status/match_eval_100_honest_BLOCKED_429.md`](match_eval_100_honest_BLOCKED_429.md)

### 3. Full serial 100

**Not executed** — would waste remaining daily quota under active 429 and yield only `upstream_error` noise.

## Re-run when quota resets (tomorrow or after limit window)

```bash
# 1) Probe first (must be 200 with stores)
python3 backend/scripts/eval_shopping_list_100.py --probe-only

# 2) Full honest serial 100
API_BASE=https://alagoas.precospublicos.ia.br CONCURRENCY=1 \
  python3 backend/scripts/eval_shopping_list_100.py \
  --out .grok/status/match_eval_100_honest.json
```

After a successful run: commit JSON + human report, mark F **DONE** in `session.md`.

## Explicitly not done (out of scope)

- Parallel 4×6 stampede
- Full UI matrix
- Relevance product fixes (C already shipped `5853031`)
- Empty-cache poison fix (E — parallel worker)

## Prior invalid eval

Do **not** use `f7ef373` / `match_eval_100.json` “missing” rates as coverage ground truth (operator: parallel load + empty cache poison).
