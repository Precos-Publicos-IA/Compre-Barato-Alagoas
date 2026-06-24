# `/.well-known/` files (app host)

Serve these from `alagoas.precospublicos.ia.br` (see `deploy/nginx/alagoas.precospublicos.ia.br.conf`).

**Content-Type (#288):** nginx uses **exact** `location =` blocks so
`security.txt` is `text/plain`, while `assetlinks.json` and
`apple-app-site-association` are `application/json`. After editing vhosts on the
host, `sudo nginx -t && sudo systemctl reload nginx` (CI does not rewrite host
nginx automatically).

**Deploy awareness (#289):** files here ship only when `deploy/**` is rsynced
(backend/deploycfg path in `deploy.yml`, or full `deploy/deploy.sh`). Merging
root `SECURITY.md` alone does **not** update production `security.txt`.

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
4. Deploy file + nginx; verify:

```bash
curl -sI https://alagoas.precospublicos.ia.br/.well-known/assetlinks.json
# Expect 200, application/json
adb shell pm get-app-links br.ia.precospublicos.compre_barato_alagoas
```

## `apple-app-site-association` — iOS Universal Links (#6)

Served with `Content-Type: application/json` (no file extension). Replace `TEAMID`
before production. Operators must install/reload the app-host nginx snippet for
per-file types (#288).

## `security.txt` — vulnerability contact (RFC 9116)

`deploy/well-known/security.txt` — keep `Contact` / `Expires` current; align with
repo-root `SECURITY.md` (policy text) but remember **live** file = this path after
`deploy/` rsync.

```bash
curl -sI https://alagoas.precospublicos.ia.br/.well-known/security.txt
# Expect 200, content-type text/plain (after #288 nginx snippet is on the host)
curl -s https://alagoas.precospublicos.ia.br/.well-known/security.txt | head
```

Optional live contract check (Node 18+):

```bash
APP_URL=https://alagoas.precospublicos.ia.br API_URL=https://alagoas.precospublicos.ia.br \
  OPS_REQUIRE_SECURITY_TXT=true OPS_REQUIRE_CLIENT_CONFIG=false node e2e/ops_probes.js
```

## `robots.txt` — crawler policy (#130)

Shipped at the Flutter/web root (`frontend/web/robots.txt`) and synced with the web build.
