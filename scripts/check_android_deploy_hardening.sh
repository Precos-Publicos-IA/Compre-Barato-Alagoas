#!/usr/bin/env bash
# Structural checks for Android/deploy hardening batch (#123 #125 #126 #127 #130).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

check_grep() {
  local file="$1" pat="$2" msg="$3"
  if ! grep -qE "$pat" "$file"; then
    echo "FAIL: $msg ($file)" >&2
    fail=1
  fi
}

check_grep "$root/frontend/android/app/src/main/AndroidManifest.xml" \
  'allowBackup="false"' "main manifest must disable backup (#127)"
check_grep "$root/frontend/android/app/src/main/AndroidManifest.xml" \
  'networkSecurityConfig' "main manifest must set networkSecurityConfig (#123)"
if grep -q 'usesCleartextTraffic="true"' "$root/frontend/android/app/src/main/AndroidManifest.xml"; then
  echo "FAIL: main manifest must not set usesCleartextTraffic=true (#123)" >&2
  fail=1
fi
check_grep "$root/frontend/android/app/src/main/AndroidManifest.xml" \
  'android:scheme="uber"' "queries must include uber scheme (#126)"
check_grep "$root/frontend/android/app/src/main/AndroidManifest.xml" \
  'taxis99' "queries must include taxis99 (#126)"

[[ -f "$root/frontend/android/app/src/main/res/xml/network_security_config.xml" ]] || {
  echo "FAIL: missing main network_security_config.xml" >&2; fail=1; }
check_grep "$root/frontend/android/app/src/main/res/xml/network_security_config.xml" \
  'cleartextTrafficPermitted="false"' "release cleartext denied (#123)"

[[ -f "$root/deploy/well-known/assetlinks.json" ]] || {
  echo "FAIL: missing assetlinks.json (#125)" >&2; fail=1; }
check_grep "$root/deploy/well-known/assetlinks.json" \
  'br.ia.precospublicos.compre_barato_alagoas' "assetlinks package name (#125)"
# Warn (not fail) when production fingerprints are still placeholders (#257).
# Operators must replace these before App Links verify; CI still surfaces the debt.
if grep -qE 'REPLACE_WITH_' "$root/deploy/well-known/assetlinks.json" 2>/dev/null; then
  echo "WARN: assetlinks.json still has REPLACE_WITH_* fingerprints (#257) — App Links will not verify in production until operators set real SHA-256 cert fingerprints (see deploy/well-known/README.md)." >&2
fi
if [[ -f "$root/deploy/well-known/apple-app-site-association" ]]; then
  if grep -qE 'TEAMID' "$root/deploy/well-known/apple-app-site-association" 2>/dev/null; then
    echo "WARN: apple-app-site-association still has TEAMID placeholder (#6) — replace with Apple Team ID before Universal Links production." >&2
  fi
fi

check_grep "$root/deploy/nginx/alagoas.precospublicos.ia.br.conf" \
  '\.well-known' "nginx must serve /.well-known/ (#125)"
check_grep "$root/deploy/nginx/alagoas.precospublicos.ia.br.conf" \
  'X-Robots-Tag' "nginx API location should set X-Robots-Tag (#130)"

# Admin/docs static hosts should carry baseline security headers (#208).
for vhost in \
  "$root/deploy/nginx/admin.alagoas.precospublicos.ia.br.conf" \
  "$root/deploy/nginx/docs.alagoas.precospublicos.ia.br.conf"; do
  [[ -f "$vhost" ]] || { echo "FAIL: missing $vhost" >&2; fail=1; continue; }
  check_grep "$vhost" 'X-Content-Type-Options' "static vhost should set nosniff (#208)"
  check_grep "$vhost" 'X-Frame-Options' "static vhost should set X-Frame-Options (#208)"
  check_grep "$vhost" 'Referrer-Policy' "static vhost should set Referrer-Policy (#208)"
done

[[ -f "$root/frontend/web/robots.txt" ]] || {
  echo "FAIL: missing frontend/web/robots.txt (#130)" >&2; fail=1; }
check_grep "$root/frontend/web/robots.txt" 'Disallow: /api/' "robots disallow /api/ (#130)"

if [[ "$fail" -ne 0 ]]; then exit 1; fi
echo "OK: android/deploy hardening structural checks passed"
