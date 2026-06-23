#!/usr/bin/env bash
# Start mock backend + static admin/docs servers, run the full headless suite, tear down.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
E2E="$ROOT/e2e"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token-0123456789}"
API_PORT="${API_PORT:-8000}"
ADMIN_PORT="${ADMIN_PORT:-8081}"
DOCS_PORT="${DOCS_PORT:-8082}"
API_URL="http://127.0.0.1:${API_PORT}"
ADMIN_URL="http://127.0.0.1:${ADMIN_PORT}"
DOCS_URL="http://127.0.0.1:${DOCS_PORT}"

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

echo "[run_local] installing e2e deps…"
cd "$E2E"
if [[ ! -d node_modules/puppeteer ]]; then
  npm install --silent
fi

echo "[run_local] starting backend on :${API_PORT} (ADMIN_TOKEN set)…"
cd "$ROOT/backend"
PY="$ROOT/backend/.venv/bin/python"
if [[ ! -x "$PY" ]]; then PY=python3; fi
ADMIN_TOKEN="$ADMIN_TOKEN" \
USE_MOCK_SEFAZ=true USE_MOCK_LLM=true ENVIRONMENT=development \
CORS_ORIGINS='*' DAILY_SEARCH_LIMIT=0 \
LOCAL_HOST=127.0.0.1 LOCAL_PORT="$API_PORT" \
"$PY" run_local.py >/tmp/cba-e2e-api.log 2>&1 &
PIDS+=($!)

echo "[run_local] serving admin-frontend on :${ADMIN_PORT}…"
python3 -m http.server "$ADMIN_PORT" --directory "$ROOT/admin-frontend" \
  >/tmp/cba-e2e-admin.log 2>&1 &
PIDS+=($!)

echo "[run_local] serving docs on :${DOCS_PORT}…"
python3 -m http.server "$DOCS_PORT" --directory "$ROOT/docs" \
  >/tmp/cba-e2e-docs.log 2>&1 &
PIDS+=($!)

echo "[run_local] waiting for API…"
for i in $(seq 1 60); do
  if curl -sf "$API_URL/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
  if [[ "$i" -eq 60 ]]; then
    echo "[run_local] API did not become ready; log:"
    tail -n 40 /tmp/cba-e2e-api.log || true
    exit 1
  fi
done

export API_URL ADMIN_URL DOCS_URL ADMIN_TOKEN
cd "$E2E"
echo "[run_local] running full suite…"
node full.js
status=$?
echo "[run_local] screenshots in $E2E/screenshots/"
exit "$status"
