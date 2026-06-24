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

check_grep "$root/deploy/nginx/alagoas.precospublicos.ia.br.conf" \
  '\.well-known' "nginx must serve /.well-known/ (#125)"
check_grep "$root/deploy/nginx/alagoas.precospublicos.ia.br.conf" \
  'X-Robots-Tag' "nginx API location should set X-Robots-Tag (#130)"

[[ -f "$root/frontend/web/robots.txt" ]] || {
  echo "FAIL: missing frontend/web/robots.txt (#130)" >&2; fail=1; }
check_grep "$root/frontend/web/robots.txt" 'Disallow: /api/' "robots disallow /api/ (#130)"

if [[ "$fail" -ne 0 ]]; then exit 1; fi
echo "OK: android/deploy hardening structural checks passed"
