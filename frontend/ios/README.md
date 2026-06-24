# iOS target (scaffold, in-scope)

Native iPhone support is **in-scope**, but this directory is **not** yet a complete
`flutter create --platforms=ios` tree (issue **#4** — needs a Mac + Xcode for
Runner.xcodeproj, Podfile, assets, IPA/TestFlight).

## What is here today

| File / work | Purpose | Issues |
|-------------|---------|--------|
| `Runner/Info.plist` | `NSMicrophoneUsageDescription`, `NSSpeechRecognitionUsageDescription`, `NSLocationWhenInUseUsageDescription` | #5 |
| `Runner/Info.plist` | `LSApplicationQueriesSchemes` (`uber`, `taxis99`, `99app`, `comgooglemaps`, `maps`, `http`, `https`) | #10 |
| `Runner/Info.plist` | `ITSAppUsesNonExemptEncryption` = false (export compliance seed) | #187 |
| `Runner/Info.plist` | `UILaunchStoryboardName` / `UIMainStoryboardFile` + orientation arrays | #280 |
| `Runner/InfoPlist.strings` | pt-BR copies of the privacy strings | #5 |
| Full `flutter create --platforms=ios` / pods / IPA / storyboards / Assets | Complete target | #4 |
| iOS Keychain options (Dart) | Device token storage | #9 |
| Apple Maps preference (Dart) | Store actions | #8 |
| Universal Links / AASA (deploy) | Share links | #6 |
| `CFBundleURLTypes` / custom scheme fallback | Not seeded (https-only App Links/AASA planned) | #285 |
| `PrivacyInfo.xcprivacy` | Not present | #242 |

### Storyboard / asset expectation (#280)

`Info.plist` references **`LaunchScreen`** and **`Main`** storyboards and iPhone
portrait / iPad multi-orientation keys, but this scaffold does **not** ship
`LaunchScreen.storyboard`, `Main.storyboard`, `Assets.xcassets`, or
`Runner.xcodeproj`. That is **expected** until a Mac runs `flutter create`.

Do **not** remove those plist keys here — `flutter create` will add the matching
resources. Your job on Mac is to **re-merge** privacy/query/encryption seeds if
create overwrites `Info.plist`.

## Completing the iOS project (Mac)

```bash
cd frontend
# Snapshot seeds first (this incomplete tree only has Runner/Info*.plist + README).
cp ios/Runner/Info.plist /tmp/cba-Info.plist.seed
cp ios/Runner/InfoPlist.strings /tmp/cba-InfoPlist.strings.seed 2>/dev/null || true

flutter create --platforms=ios .
# Re-merge privacy + LSApplicationQueriesSchemes + ITSAppUsesNonExemptEncryption
# (+ any other keys you care about) from /tmp/cba-Info.plist.seed into ios/Runner/Info.plist
# if flutter create overwrote them. Then:
python3 ../scripts/verify_ios_info_plist.py   # from repo root: python3 scripts/verify_ios_info_plist.py

flutter pub get
cd ios && pod install && cd ..
flutter run -d <iphone-or-simulator>
# or
flutter build ipa --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br
```

Post-create checklist (Mac/operator):

1. Confirm `LaunchScreen.storyboard` / `Assets.xcassets` exist and match brand green if desired.
2. Add **Associated Domains** capability for `applinks:alagoas.precospublicos.ia.br` when AASA is live (#6, replace `TEAMID` in `deploy/well-known/apple-app-site-association`).
3. Add `PrivacyInfo.xcprivacy` before App Store (#242).
4. Decide custom URL scheme policy (#285) vs https-only share links.
5. Follow App Store Connect runbook when written (#270); policy bumps use `docs/ops-policy-version-release.md` (#283).

Bundle id (match Android): `br.ia.precospublicos.compre_barato_alagoas`.

## Verify without Xcode (Linux-friendly)

```bash
# From repo root
python3 scripts/verify_ios_info_plist.py   # Info.plist keys (#5/#10)
python3 scripts/verify_ios_webkit_e2e.py   # docs + checklist + scaffold (#16)
```

Storyboards/Xcode project **cannot** be fully validated on Linux — only seeds + docs.

## Web / Safari note

Until a full `ios/` Runner ships, the primary iPhone path is **Safari / PWA** on
`alagoas.precospublicos.ia.br`. Headless CI e2e uses **Chromium** (mobile viewport),
not Safari/WebKit — see `e2e/README.md` and `.github/ISSUE_TEMPLATE/iphone-safari-checklist.md`.

## Related app code

- Voice / mic: `lib/features/search/voice_input.dart`
- Location: `lib/core/location.dart`
- Uber / 99 / maps schemes: `lib/features/results/store_actions.dart`
- Android parallel permissions: `android/app/src/main/AndroidManifest.xml`
