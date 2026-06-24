#!/usr/bin/env bash
# Structural check: public HTML shells must disable Safari telephone auto-link (#102).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
files=(
  "$root/frontend/web/index.html"
  "$root/frontend/web/privacy.html"
  "$root/admin-frontend/index.html"
  "$root/docs/index.html"
  "$root/docs/seguranca-postura.html"
  "$root/docs/seguranca-e-dados.html"
  "$root/docs/lgpd-medicao-de-uso.html"
)
needle='name="format-detection"'
needle2='content="telephone=no"'
fail=0
for f in "${files[@]}"; do
  if ! grep -q "$needle" "$f" || ! grep -q "$needle2" "$f"; then
    echo "FAIL: missing format-detection telephone=no in $f" >&2
    fail=1
  fi
done
if [[ "$fail" -ne 0 ]]; then
  exit 1
fi
echo "OK: format-detection telephone=no present in ${#files[@]} HTML shells"
