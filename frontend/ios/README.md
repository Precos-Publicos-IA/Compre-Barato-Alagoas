# iOS target (scaffold)

This directory holds **privacy and URL-scheme configuration** required before a full
Xcode/Flutter iOS project can ship on iPhone. It is **not** yet a complete
`flutter create --platforms=ios` tree (see issue #4 — needs a Mac + Xcode to
finish Runner.xcodeproj, Podfile, assets, etc.).

## What is here today

| File | Purpose | Issues |
|------|---------|--------|
| `Runner/Info.plist` | `NSMicrophoneUsageDescription`, `NSSpeechRecognitionUsageDescription`, `NSLocationWhenInUseUsageDescription` | #5 |
| `Runner/Info.plist` | `LSApplicationQueriesSchemes` (`uber`, `taxis99`, `99app`, `comgooglemaps`, `maps`, `http`, `https`) | #10 |
| `Runner/InfoPlist.strings` | pt-BR copies of the privacy strings | #5 |

## Completing the iOS project (Mac)

```bash
cd frontend
flutter create --platforms=ios .
# If flutter create overwrites Info.plist, re-merge the keys from git history
# or from this README's table. Then:
flutter pub get
cd ios && pod install && cd ..
flutter run -d <iphone-or-simulator>
# or
flutter build ipa --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br
```

Bundle id (match Android): `br.ia.precospublicos.compre_barato_alagoas`.

## Verify without Xcode

From the repo root (Linux-friendly structural check):

```bash
python3 scripts/verify_ios_info_plist.py
```

## Related app code

- Voice / mic: `lib/features/search/voice_input.dart`
- Location: `lib/core/location.dart`
- Uber / 99 / maps schemes: `lib/features/results/store_actions.dart`
- Android parallel permissions: `android/app/src/main/AndroidManifest.xml`
