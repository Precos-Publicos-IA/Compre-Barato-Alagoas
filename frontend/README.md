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

## Notes

- Android permissions: `INTERNET`, `RECORD_AUDIO` (voice), location. `usesCleartextTraffic` is on
  to allow `http://` LAN backends during development; production uses HTTPS.
- iOS privacy keys (English): mic, speech recognition, location-when-in-use — see `ios/Runner/Info.plist`.
- iOS URL schemes: `uber`, `taxis99`, `99app`, `comgooglemaps`, `maps` — required for `canLaunchUrl` / external apps.
- App id: `br.ia.precospublicos.compre_barato_alagoas`.
