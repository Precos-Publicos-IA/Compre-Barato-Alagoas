#!/usr/bin/env bash
# Boot mock backend + static admin/docs (same as run_local.sh), run prioritized matrix capture.
# Optional APP_URL for Flutter web; optional MATRIX_FORMATS / RECORD_VIDEO (see matrix_capture.js).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
E2E="$ROOT/e2e"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token-0123456789}"
API_PORT="${API_PORT:-8000}"
ADMIN_PORT="${ADMIN_PORT:-8081}"
DOCS_PORT="${DOCS_PORT:-8082}"
APP_PORT="${APP_PORT:-8080}"
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

cd "$E2E"
if [[ -d /opt/ci/e2e/node_modules/puppeteer ]]; then
  export NODE_PATH="${NODE_PATH:-/opt/ci/e2e/node_modules}"
  echo "[run_matrix_local] using pre-baked /opt/ci toolchain"
elif [[ ! -d node_modules/puppeteer ]]; then
  echo "[run_matrix_local] installing e2e deps…"
  npm install --silent
fi

echo "[run_matrix_local] starting backend on :${API_PORT}…"
cd "$ROOT/backend"
PY=python3
if [[ -x "$ROOT/backend/.venv/bin/python" ]]; then PY="$ROOT/backend/.venv/bin/python"; fi
ADMIN_TOKEN="$ADMIN_TOKEN" \
USE_MOCK_SEFAZ=true USE_MOCK_LLM=true ENVIRONMENT=development \
CORS_ORIGINS='*' DAILY_SEARCH_LIMIT=0 \
LOCAL_HOST=127.0.0.1 LOCAL_PORT="$API_PORT" \
"$PY" run_local.py >/tmp/cba-matrix-api.log 2>&1 &
PIDS+=($!)

echo "[run_matrix_local] serving admin-frontend on :${ADMIN_PORT}…"
python3 -m http.server "$ADMIN_PORT" --directory "$ROOT/admin-frontend" \
  >/tmp/cba-matrix-admin.log 2>&1 &
PIDS+=($!)

echo "[run_matrix_local] serving docs on :${DOCS_PORT}…"
python3 -m http.server "$DOCS_PORT" --directory "$ROOT/docs" \
  >/tmp/cba-matrix-docs.log 2>&1 &
PIDS+=($!)

# Optional Flutter web: use APP_URL if set, else serve frontend/build/web when present
if [[ -z "${APP_URL:-}" ]]; then
  WEB_DIR="$ROOT/frontend/build/web"
  if [[ -f "$WEB_DIR/index.html" ]]; then
    echo "[run_matrix_local] serving Flutter web build on :${APP_PORT}…"
    python3 -m http.server "$APP_PORT" --directory "$WEB_DIR" \
      >/tmp/cba-matrix-app.log 2>&1 &
    PIDS+=($!)
    APP_URL="http://127.0.0.1:${APP_PORT}"
  else
    echo "[run_matrix_local] no Flutter web build (frontend/build/web) — capture admin/docs/api only"
  fi
fi

echo "[run_matrix_local] waiting for API…"
for i in $(seq 1 60); do
  if curl -sf "$API_URL/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
  if [[ "$i" -eq 60 ]]; then
    echo "[run_matrix_local] API not ready; log:"
    tail -n 40 /tmp/cba-matrix-api.log || true
    exit 1
  fi
done

export API_URL ADMIN_URL DOCS_URL ADMIN_TOKEN
[[ -n "${APP_URL:-}" ]] && export APP_URL
export MATRIX_FORMATS="${MATRIX_FORMATS:-priority}"
export RECORD_VIDEO="${RECORD_VIDEO:-1}"
export MATRIX_HOLD_MS="${MATRIX_HOLD_MS:-450}"

cd "$E2E"
echo "[run_matrix_local] running matrix_capture.js…"
if [[ -f /opt/ci/e2e/node_modules/puppeteer/package.json ]]; then
  NODE_PATH=/opt/ci/e2e/node_modules node matrix_capture.js
  status=$?
else
  node matrix_capture.js
  status=$?
fi
echo "[run_matrix_local] viewports → $E2E/screenshots/viewports/"
echo "[run_matrix_local] recordings → $E2E/screenshots/web/e2e/recordings/"
exit "$status"
