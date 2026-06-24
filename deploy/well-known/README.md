# Well-known files (Android App Links + iOS Universal Links)

Serve these at the **app origin** `https://alagoas.precospublicos.ia.br/.well-known/…`
(same host as share links `/abrir/<uuid>`).

| File | Platform | Notes |
|------|----------|--------|
| `apple-app-site-association` | iOS Universal Links | **No** `.json` suffix. Must be served as `application/json` (or `application/pkcs7-mime` if signed). Replace `TEAMID` with the Apple Developer Team ID once the iOS app exists in App Store Connect / developer portal. Paths scoped to `/abrir/*` only (mirrors Android `pathPrefix`). |
| `assetlinks.json` | Android App Links | Add when you have the release signing cert SHA-256 fingerprint(s). Not committed here yet (production fingerprints are deploy-specific). |

## nginx

`deploy/nginx/alagoas.precospublicos.ia.br.conf` includes a `location ^~ /.well-known/` block that serves this directory. Copy/symlink `deploy/well-known/` onto the host (e.g. `/srv/apps/compre-barato-alagoas/well-known/`) and point the nginx `alias` there if your deploy layout differs.

## iOS project checklist (see issues #4, #5, #6, #10)

1. Generate `frontend/ios/` (`flutter create --platforms=ios`).
2. Enable Associated Domains entitlement: `applinks:alagoas.precospublicos.ia.br`.
3. Set real `appID` (`TEAMID.bundleid`) in `apple-app-site-association`.
4. Add `Info.plist` privacy strings + `LSApplicationQueriesSchemes` for Uber/99/maps.
