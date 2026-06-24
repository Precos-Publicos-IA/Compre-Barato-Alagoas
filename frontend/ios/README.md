# iOS target (in-scope scaffold)

Native iPhone support is **in-scope** for this product, but the full Flutter
`ios/` Xcode project is not complete yet (issue **#4** — needs macOS + Xcode).

| Work | Issues |
|------|--------|
| Privacy usage strings + `LSApplicationQueriesSchemes` in `Runner/Info.plist` | #5, #10 |
| Full `flutter create --platforms=ios` / pods / IPA | #4 |
| iOS Keychain options (Dart) | #9 |
| Apple Maps preference (Dart) | #8 |
| Universal Links / AASA (deploy) | #6 |

## Mac — complete the target

```bash
cd frontend
flutter create --platforms=ios .
# Preserve/merge Info.plist privacy + LSApplicationQueriesSchemes keys
flutter pub get && (cd ios && pod install)
flutter run -d <iphone-or-simulator>
flutter build ipa --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br
```

## Verification without Xcode

```bash
# From repo root
python3 scripts/verify_ios_info_plist.py   # if Info.plist present (#5/#10)
python3 scripts/verify_ios_webkit_e2e.py   # docs + checklist + scaffold (#16)
```

## Web / Safari note

Production users on iPhone often use **Safari/PWA** (`frontend/web/`), not the
native shell. Headless e2e in `e2e/` drives **Chromium** with a mobile viewport
only — see `e2e/README.md` and issue **#16**.
