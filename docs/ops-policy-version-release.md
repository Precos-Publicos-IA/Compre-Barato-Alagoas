# Ops: bumping `POLICY_VERSION` / LGPD policy text — #283

Consent records store `policy_version`. The Flutter app sends
`AppConfig.policyVersion` (compile-time in `frontend/lib/core/config.dart`) and
treats server/client drift as requiring **fresh consent** for cloud features
(#63 / #188 area). Backend default is `Settings.policy_version` /
`POLICY_VERSION` in `.env` (see `.env.example`).

A careless bump can lock consented users out of cloud lists until they accept
again, or create inconsistent legal records if only one layer is updated.

## Order of operations (release checklist)

Do these in order; tick in the PR/issue before deploy.

1. **Legal / copy**
   - Update policy/terms text in `frontend/web/privacy.html`.
   - Update or link relevant `docs/` LGPD pages (`seguranca-e-dados.html`, etc.).
   - Note effective date in `CHANGELOG.md` under Unreleased.

2. **Choose the new version string**
   - Prefer ISO date form already used: `YYYY-MM-DD` (example: `2026-06-06`).
   - Must fit backend validation (`max_length=32` on device consent schema).

3. **Backend / server config**
   - Set `POLICY_VERSION` in production `.env` (and document in `.env.example` if
     the default in code changes).
   - Redeploy/restart API so new consents persist the new version.

4. **App / web client**
   - Set `AppConfig.policyVersion` in `frontend/lib/core/config.dart` to the **same**
     string.
   - Rebuild and deploy Flutter **web** (and APK if you distribute one) so clients
     send the new version.
   - Optional: set `MIN_APP_VERSION` / `MIN_WEB_BUILD` via `client-config` (#268)
     if old binaries must be forced off before legal cutover.

5. **Verify**
   - `GET /api/v1/client-config` (when deployed) returns expected `policy_version`.
   - Fresh consent with a test device token stores the new version (`GET /api/v1/device/me`).
   - Old consented device without app update: confirm product behavior (hard
     re-consent vs soft prompt — today is effectively hard for cloud paths).

6. **Communicate**
   - Short note in `CHANGELOG.md`.
   - If you maintain Play/App Store listings, update privacy questionnaire if data
     practices changed (#262 / #270).

## Staged rollout (recommended product follow-up)

Not implemented yet; track in #283 comments / future PR:

- Server accepts previous `policy_version` for `T` days while showing an in-app
  “política atualizada” sheet (soft) before blocking cloud save.
- Admin metric: count of consents per `policy_version`.

## Related

- `frontend/lib/core/config.dart` — `policyVersion`
- `backend/app/config.py` — `policy_version`
- `backend/app/api/routes/device.py` — consent / `device/me`
- `docs/lgpd-medicao-de-uso.html` — measurement LIA (separate from full policy text)
- #276 — DPO/titular process docs still incomplete
