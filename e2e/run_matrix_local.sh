#!/usr/bin/env bash
# Boot mock backend + static admin/docs + Flutter web, run full matrix capture.
#
# Default = FULL matrix (all formats × all screens) — ship path for residual close.
# Debug/fast: MATRIX_FORMATS=priority MATRIX_SCREENS=admin,docs
#
# Optional handheld Phase A after Puppeteer:
#   RUN_EMULATOR=1  → also node matrix_emulator.js (adb screenrecord + input)
#
# Env: MATRIX_FORMATS MATRIX_SCREENS RECORD_VIDEO CONCURRENCY MATRIX_HOLD_MS
#      APP_URL API_PORT ADMIN_PORT DOCS_PORT APP_PORT BUILD_WEB=1|0
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
E2E="$ROOT/e2e"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token-0123456789}"
API_PORT="${API_PORT:-8000}"
ADMIN_PORT="${ADMIN_PORT:-8081}"
DOCS_PORT="${DOCS_PORT:-8082}"
APP_PORT="${APP_PORT:-18090}"
API_URL="http://127.0.0.1:${API_PORT}"
ADMIN_URL="http://127.0.0.1:${ADMIN_PORT}"
DOCS_URL="http://127.0.0.1:${DOCS_PORT}"
BUILD_WEB="${BUILD_WEB:-1}"
RUN_EMULATOR="${RUN_EMULATOR:-0}"
FLUTTER_BIN="${FLUTTER_BIN:-}"
if [[ -z "$FLUTTER_BIN" ]]; then
  if command -v flutter >/dev/null 2>&1; then FLUTTER_BIN=flutter
  elif [[ -x /home/viny/flutter/bin/flutter ]]; then FLUTTER_BIN=/home/viny/flutter/bin/flutter
  fi
fi

PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

port_free() {
  local p="$1"
  ! (echo >/dev/tcp/127.0.0.1/"$p") >/dev/null 2>&1
}

cd "$E2E"
if [[ -d /opt/ci/e2e/node_modules/puppeteer ]]; then
  export NODE_PATH="${NODE_PATH:-/opt/ci/e2e/node_modules}"
  echo "[run_matrix_local] using pre-baked /opt/ci toolchain"
elif [[ ! -d node_modules/puppeteer ]]; then
  echo "[run_matrix_local] installing e2e deps…"
  npm install --silent
fi

# --- Flutter web build (product screens need APP_URL) ---
WEB_DIR="$ROOT/frontend/build/web"
if [[ -z "${APP_URL:-}" ]]; then
  if [[ "$BUILD_WEB" == "1" && -n "$FLUTTER_BIN" ]]; then
    if [[ ! -f "$WEB_DIR/index.html" || "${FORCE_WEB_BUILD:-0}" == "1" ]]; then
      echo "[run_matrix_local] flutter build web --release (API_BASE_URL=${API_URL})…"
      (cd "$ROOT/frontend" && "$FLUTTER_BIN" build web --release \
        --dart-define=API_BASE_URL="$API_URL" \
        --no-wasm-dry-run)
    else
      echo "[run_matrix_local] reusing existing $WEB_DIR (FORCE_WEB_BUILD=1 to rebuild)"
    fi
  fi
  if [[ -f "$WEB_DIR/index.html" ]]; then
    # Avoid colliding with unrelated servers on :8080 (common on shared hosts).
    if ! port_free "$APP_PORT"; then
      for try in 18090 18091 18092 8090 8091; do
        if port_free "$try"; then APP_PORT=$try; break; fi
      done
    fi
    echo "[run_matrix_local] serving Flutter web on :${APP_PORT}…"
    python3 -m http.server "$APP_PORT" --bind 127.0.0.1 --directory "$WEB_DIR" \
      >/tmp/cba-matrix-app.log 2>&1 &
    PIDS+=($!)
    APP_URL="http://127.0.0.1:${APP_PORT}"
    # Sanity: must be Compre Barato, not another app occupying the port.
    sleep 0.3
    if ! curl -sf "$APP_URL/" | head -c 400 | grep -qi 'flutter\|Compre\|main.dart.js'; then
      echo "[run_matrix_local] WARNING: $APP_URL does not look like Flutter web build"
    fi
  else
    echo "[run_matrix_local] WARNING: no Flutter web build — product screens will be missing"
    echo "  Install Flutter and re-run, or set APP_URL. Full 147 requires APP_URL."
  fi
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

export API_URL ADMIN_URL DOCS_URL ADMIN_TOKEN API_PORT ADMIN_PORT DOCS_PORT APP_PORT
[[ -n "${APP_URL:-}" ]] && export APP_URL
# Full matrix is the default ship path; priority is debug-only.
export MATRIX_FORMATS="${MATRIX_FORMATS:-all}"
export MATRIX_SCREENS="${MATRIX_SCREENS:-all}"
export RECORD_VIDEO="${RECORD_VIDEO:-1}"
export MATRIX_HOLD_MS="${MATRIX_HOLD_MS:-700}"
export CONCURRENCY="${CONCURRENCY:-2}"
export MATRIX_STRICT="${MATRIX_STRICT:-0}"
export MATRIX_RESULTS_TIMEOUT_MS="${MATRIX_RESULTS_TIMEOUT_MS:-90000}"
export PUPPETEER_PROTOCOL_TIMEOUT_MS="${PUPPETEER_PROTOCOL_TIMEOUT_MS:-300000}"

cd "$E2E"
echo "[run_matrix_local] running matrix_capture.js (FORMATS=$MATRIX_FORMATS SCREENS=$MATRIX_SCREENS CONCURRENCY=$CONCURRENCY)…"
if [[ -f /opt/ci/e2e/node_modules/puppeteer/package.json ]]; then
  NODE_PATH=/opt/ci/e2e/node_modules node matrix_capture.js
  status=$?
else
  node matrix_capture.js
  status=$?
fi

if [[ "$RUN_EMULATOR" == "1" ]]; then
  echo "[run_matrix_local] RUN_EMULATOR=1 → matrix_emulator.js (Phase A handheld)…"
  # Emulator path: touch formats only (unless overridden)
  export MATRIX_FORMATS="${EMULATOR_MATRIX_FORMATS:-handheld}"
  set +e
  node matrix_emulator.js
  emu_status=$?
  set -e
  if [[ "$emu_status" -ne 0 ]]; then
    echo "[run_matrix_local] emulator path exit $emu_status (CAPTURE may be partial)"
    status=$emu_status
  fi
fi

echo "[run_matrix_local] viewports → $E2E/screenshots/viewports/"
echo "[run_matrix_local] recordings → $E2E/screenshots/web/e2e/recordings/"
echo "[run_matrix_local] CAPTURE_OK layer only — next: A4b/A6 critiques under qa_success_criteria.json"
exit "$status"
