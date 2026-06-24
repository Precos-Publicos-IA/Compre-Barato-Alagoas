# `/.well-known/` files (app host)

Serve these from `alagoas.precospublicos.ia.br` (see `deploy/nginx/alagoas.precospublicos.ia.br.conf`).

## `assetlinks.json` — Android App Links (#125)

Verifies that `https://alagoas.precospublicos.ia.br/abrir/*` may open the APK
(`br.ia.precospublicos.compre_barato_alagoas`) without a disambiguation dialog.

1. Build/sign the release APK (do **not** ship debug-signed builds to end users long-term — #124).
2. Extract the signing cert SHA-256:

```bash
# Debug keystore (local only)
keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey \
  -storepass android -keypass android | grep SHA256

# Release keystore (operator-managed)
keytool -list -v -keystore /path/to/release.keystore -alias YOUR_ALIAS
```

3. Replace `REPLACE_WITH_*_SHA256_CERT_FINGERPRINT` in `assetlinks.json` with colon-less
   or colon-separated form as required by Google (Play Console also shows App signing key cert).
   **Do not deploy placeholders to production** — Digital Asset Links verification fails
   and `/abrir` links open in the browser only (#257). `scripts/check_android_deploy_hardening.sh`
   prints a WARN while placeholders remain (CI does not hard-fail, because fingerprints are
   operator/keystore secrets not committed here).
4. Deploy file + nginx; verify:

```bash
curl -sI https://alagoas.precospublicos.ia.br/.well-known/assetlinks.json
# Expect 200, application/json; body must not contain REPLACE_WITH_
# Optional live check (after real fingerprints are live):
# curl -s "https://digitalassetlinks.googleapis.com/v1/statements:list?source.web.site=https://alagoas.precospublicos.ia.br&relation=delegate_permission/common.handle_all_urls"
adb shell pm get-app-links br.ia.precospublicos.compre_barato_alagoas
```

## `apple-app-site-association` — iOS Universal Links (#6)

If present in this directory (or added in a sibling PR), same nginx `/.well-known/` location
serves it. Replace `TEAMID` before production (hardening script WARNs while present).

## `robots.txt` — crawler policy (#130)

Shipped at the Flutter/web root (`frontend/web/robots.txt`) and synced with the web build.
