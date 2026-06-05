# Frontend — Compre Barato Alagoas

Flutter app (Android + web) for the price-comparison experience. Riverpod state,
OpenStreetMap map (no API key), functional voice input. See the [root README](../README.md).

## Run

```bash
flutter pub get
flutter test                       # unit + widget tests

# Point at a backend (defaults to the production domain otherwise):
flutter run --dart-define=API_BASE_URL=http://<your-lan-ip>:8000
```

## On a physical phone

```bash
# Backend must listen on 0.0.0.0 and the phone must reach your machine on the LAN.
flutter build apk --debug --dart-define=API_BASE_URL=http://<your-lan-ip>:8000
adb -s <device-id> install -r build/app/outputs/flutter-apk/app-debug.apk
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

- Android permissions: `INTERNET`, `RECORD_AUDIO` (voice). `usesCleartextTraffic` is on
  to allow `http://` LAN backends during development; production uses HTTPS.
- App id: `br.ia.precospublicos.compre_barato_alagoas`.
