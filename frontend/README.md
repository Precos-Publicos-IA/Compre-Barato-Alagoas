# Frontend — Compre Barato Alagoas

Flutter app (Android + web; **iOS scaffold** for privacy/URL schemes only — see
[`ios/README.md`](ios/README.md)) for the price-comparison experience. Riverpod
state, OpenStreetMap map (no API key), functional voice input. See the
[root README](../README.md).

## Run

```bash
flutter pub get
flutter test                       # unit + widget tests

# Point at a backend (defaults to the production domain otherwise):
flutter run --dart-define=API_BASE_URL=http://<your-lan-ip>:8000
```

## On a physical phone (Android)

```bash
# Backend must listen on 0.0.0.0 and the phone must reach your machine on the LAN.
flutter build apk --debug --dart-define=API_BASE_URL=http://<your-lan-ip>:8000
adb -s <device-id> install -r build/app/outputs/flutter-apk/app-debug.apk
```

## iOS (scaffold / Mac)

`ios/Runner/Info.plist` already includes privacy usage strings (#5) and
`LSApplicationQueriesSchemes` for Uber/99/maps (#10). Completing the Xcode
project still requires a Mac:

```bash
# On macOS with Xcode + CocoaPods:
flutter create --platforms=ios .   # merge/preserve Info.plist keys if overwritten
cd ios && pod install && cd ..
flutter run -d <iphone-or-simulator>
flutter build ipa --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br
```

Structural check (no Mac/Xcode needed):

```bash
python3 ../scripts/verify_ios_info_plist.py   # from frontend/, or run from repo root
```

## On-device end-to-end test

```bash
flutter test integration_test/app_test.dart \
  --dart-define=API_BASE_URL=http://<your-lan-ip>:8000 -d <device-id>
```

## Web build (served by nginx in production)

```bash
flutter build web --release \
  --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br
```

### PWA / caching / updates (#199, #106, #158)

- **Install:** `web/manifest.json` + `index.html` `beforeinstallprompt` (Chrome/Android) and iOS A2HS meta tags.
  Offline/service-worker product behaviour is still tracked in #158; do not assume a full offline shell ships by default.
- **Build:** default `flutter build web` may emit `flutter_service_worker.js` depending on Flutter version/flags.
  If you need a specific strategy, pass e.g. `--pwa-strategy=offline-first` (or `none`) explicitly and document it in the deploy PR.
- **Deploy cache policy (recommended):**
  - **Short / no-cache:** `index.html`, `flutter_bootstrap.js`, `flutter_service_worker.js`, `manifest.json` (so users pick up new releases without waiting for a stale SW).
  - **Long + immutable:** hashed `main.dart.js`, CanvasKit/wasm, `assets/**` (content-addressed by Flutter build).
- **After deploy:** iOS Safari A2HS and Android WebAPK can retain old shells; operators should verify one hard-refresh and one installed-PWA launch. A future in-app “Nova versão — atualizar” banner is desirable if a SW is enabled.
- **Robots:** `web/robots.txt` is copied with the build; nginx must serve it as a real file (not SPA-fallback only).

## Notes

- Android permissions: `INTERNET`, `RECORD_AUDIO` (voice), location. Cleartext is restricted via
  `network_security_config` (debug/dev hosts only in current hardening); production uses HTTPS.
- iOS privacy keys (pt-BR): mic, speech recognition, location-when-in-use — see `ios/Runner/Info.plist`.
- iOS URL schemes: `uber`, `taxis99`, `99app`, `comgooglemaps`, `maps` — required for `canLaunchUrl` / external apps.
- iOS export compliance scaffold: `ITSAppUsesNonExemptEncryption` = false (#187); confirm in App Store Connect.
- App id: `br.ia.precospublicos.compre_barato_alagoas`.
