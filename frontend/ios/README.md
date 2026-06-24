# iOS target (scaffold, in-scope)

Native iPhone support is **in-scope**, but this directory is **not** yet a complete
`flutter create --platforms=ios` tree (issue **#4** — needs a Mac + Xcode for
Runner.xcodeproj, Podfile, assets, IPA/TestFlight).

## What is here today

| File / work | Purpose | Issues |
|-------------|---------|--------|
| `Runner/Info.plist` | `NSMicrophoneUsageDescription`, `NSSpeechRecognitionUsageDescription`, `NSLocationWhenInUseUsageDescription` | #5 |
| `Runner/Info.plist` | `LSApplicationQueriesSchemes` (`uber`, `taxis99`, `99app`, `comgooglemaps`, `maps`, `http`, `https`) | #10 |
| `Runner/Info.plist` | `ITSAppUsesNonExemptEncryption` = `false` (HTTPS/OS crypto only; ops must re-check if that changes) | #313 |
| `Runner/InfoPlist.strings` | pt-BR copies of the privacy strings | #5 |
| Full `flutter create --platforms=ios` / pods / IPA | Complete target | #4 |
| iOS Keychain options (Dart) | Device token storage | #9 |
| Apple Maps preference (Dart) | Store actions | #8 |
| Universal Links / AASA (deploy) | Share links | #6 |

## Completing the iOS project (Mac)

```bash
cd frontend
flutter create --platforms=ios .
# If flutter create overwrites Info.plist, re-merge privacy + LSApplicationQueriesSchemes
# keys from this repo (or re-run scripts/verify_ios_info_plist.py and fix).
flutter pub get
cd ios && pod install && cd ..
flutter run -d <iphone-or-simulator>
# or
flutter build ipa --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br
```

Bundle id (match Android): `br.ia.precospublicos.compre_barato_alagoas`.

## Verify without Xcode (Linux-friendly)

```bash
# From repo root
python3 scripts/verify_ios_info_plist.py   # Info.plist keys (#5/#10)
python3 scripts/verify_ios_webkit_e2e.py   # docs + checklist + scaffold (#16)
```

## Web / Safari note

Until a full `ios/` Runner ships, the primary iPhone path is **Safari / PWA** on
`alagoas.precospublicos.ia.br`. Headless CI e2e uses **Chromium** (mobile viewport),
not Safari/WebKit — see `e2e/README.md` and `.github/ISSUE_TEMPLATE/iphone-safari-checklist.md`.

## Related app code

- Voice / mic: `lib/features/search/voice_input.dart`
- Location: `lib/core/location.dart`
- Uber / 99 / maps schemes: `lib/features/results/store_actions.dart`
- Android parallel permissions: `android/app/src/main/AndroidManifest.xml`
