# Phase 0 — matching baseline snapshot

| Field | Value |
|-------|--------|
| **Date (UTC)** | 2026-07-23 |
| **Baseline tip SHA (pre-M0/M1)** | `bc5964f46b96b2b492b9c9ef7dc9683f83c2cd0c` (`bc5964f`) |
| **Product SHAs in tree** | head+wait `12b2c97` · desugar `3112eb7` · staple B2 `9ec6775` |
| **MATCH_RULES_VERSION** | `2026-07-23-head-v1` |
| **Overall eval** | [worker_w_eval_overall_report.md](worker_w_eval_overall_report.md) — **grade C+** |
| **Probe artifact** | [eval_overall_live_probes.json](eval_overall_live_probes.json) |
| **Live app** | https://alagoas.precospublicos.ia.br |
| **Method** | Live prod · CONCURRENCY=1 · n=19 probes · Maceió |

## Key rates (from overall eval 2026-07-23)

| Metric | Value | Notes |
|--------|------:|-------|
| **found_rate** (`stores>0`) | **14/19 = 73.7%** | singles + multi basket |
| **fetch_fail_rate** | **4/18 singles** (~22% singles; feijão, óleo, café, açúcar) | ~55s `items_fetch_failed` |
| **true empty** (failed=0) | 1 (detergente) | not a fetch fail |
| **p50 latency** | **~36595 ms** | cold-heavy set |
| **p95 latency** | **~55715 ms** | deadline wall |
| **good_top (soft)** | 9/14 found | arroz, ovo, banana, farinha, pão, papel, salsicha, sabão em pó, sal |
| **weak_top (soft)** | 4/14 found | leite, peito, queijo, alho |
| **HTTP 200** | 19/19 | no 429 |

## Separation (match vs fetch)

- **Match track:** among `stores>0` and `items_fetch_failed=0`, head gate fixed egg-bleed; residual weak snack/soup/sauce tops.
- **Fetch track:** staple empty often = upstream deadline, not missing catalog (multi basket can still return feijão).

## Use of this baseline

Later phases claim “improved vs baseline” against this SHA + rates. Do not grade match quality on `items_fetch_failed` rows.

## Goldens (Phase 0 freeze)

```text
pytest tests/test_intent_heads.py tests/test_relevance_quality.py -q
```

Must stay green on the M0/M1 ship SHA (recorded in worker report after commit).
