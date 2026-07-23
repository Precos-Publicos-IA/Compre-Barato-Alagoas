# W-m6-feedback — Phase 6 Product feedback wire-through

**Worker:** W-m6-feedback  
**Date:** 2026-07-23  
**Feature commit:** `acf0944` — `feat(match): wire wrong_item feedback into learn_policy`
**Scope:** backend feedback schema/route + Flutter wrong_item payload + tests  
**Out of scope:** Phase 7, admin 6.3, full UI matrix, B2 resmoke

## Definition of success

| ID | Criterion | Result | Evidence |
|----|-----------|--------|----------|
| **6-S1** | API `wrong_item` accepts **query** + **description** (or item text); validated in tests | **PASS** | `FeedbackRequest.query` / `.description`; `resolved_query()` / `resolved_description()`; `test_s1_*` in `backend/tests/test_feedback.py` |
| **6-S2** | Handler invokes `learn_policy.on_user_feedback` when fields present | **PASS** | `feedback.py` maps resolved query+description → `on_user_feedback`; `test_s2_handler_invokes_on_user_feedback_with_query_description` |
| **6-S3** | Flutter “Reportar item errado” sends **non-empty description** of offending line + **user query/label** | **PASS** | `feedback_payload.dart` + `_ReportSheet` / `ApiClient.submitFeedback`; `test/feedback_payload_test.dart` + widget test in `test/feedback_test.dart` |
| **6-S4** | Integration: seed RAG success → post wrong_item → mapping demoted/absent | **PASS** | `test_s4_wrong_item_query_description_demotes_mapping` (+ legacy demote still green) |
| **6-S5** | Feedback still **200** if learn Redis down (best-effort learn; feedback stored) | **PASS** | try/except around learn; `test_s5_feedback_200_when_learn_raises`, `test_s5_feedback_200_when_rag_store_raises` |
| **6-S6** | No device token into outcome log beyond existing privacy rules | **PASS** | `del device_token` in route; learn kwargs never include token; route does not call outcome_log; `test_s6_device_token_not_passed_to_learn_or_outcome` |

**Optional 6.3 (admin bad-label counts):** skipped (not required).

## Changes

### Backend
- `backend/app/schemas/feedback.py` — add `query`, `description`; sanitizers; `resolved_query()` / `resolved_description()` (prefer new fields; fall back to `item` / `note` for compat).
- `backend/app/api/routes/feedback.py` — resolve query/description; pass to `on_user_feedback`; keep best-effort learn; explicitly discard device token (privacy).
- `backend/tests/test_feedback.py` — 6-S1…6-S6 coverage.

### Flutter
- `frontend/lib/features/results/feedback_payload.dart` — pure helpers: `itemDescriptionsFromResults`, `wrongItemFeedbackBody`.
- `frontend/lib/data/api_client.dart` — `submitFeedback` accepts `query` + `description`.
- `frontend/lib/features/results/results_screen.dart` — pass product descriptions from results into report sheet; wrong_item submit sends query + non-empty description when offers exist.
- `frontend/test/feedback_payload_test.dart`, `frontend/test/feedback_test.dart` — payload + widget contract.

## Verification

```text
cd backend && python -m pytest tests/test_feedback.py tests/test_learn_policy.py -q
# 25 passed

cd frontend && flutter test test/feedback_payload_test.dart test/feedback_test.dart
# All tests passed (7)
```

## Safety rails
- Head-safe learn_policy only; **never** success-learn on `wrong_item` (unchanged policy).
- Learn failures do not fail the feedback ACK.
- Device token not forwarded into learn or outcome log from this path.

## Residual (not this worker)
- `leite` SEFAZ ~55s external residual (B2).
- P7 entry criteria (outcome log volume + learn_policy in prod ≥7d) **not met** — do not start Phase 7.
- Admin 6.3 optional counts not shipped.

## Status
**M6 DONE** at `acf0944` on `main`; session records the same feature SHA.
