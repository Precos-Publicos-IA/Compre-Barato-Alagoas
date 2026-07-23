#!/usr/bin/env bash
# Best-effort staple SEFAZ term-cache warm via the live search API.
#
# Called after stack health check (remote-update / CI deploy). Uses only curl so
# it runs on the VPS host without Python, Redis client, or docker exec.
# Failures are non-fatal when PREWARM_STRICT is unset/0 (default for deploy).
#
# Env:
#   API_BASE              default http://127.0.0.1:8000
#   PREWARM_BATCH_SIZE    items per POST (default 1 — avoid SEFAZ stampede)
#   PREWARM_DELAY         seconds between batches (default 1.5)
#   PREWARM_TIMEOUT       curl max-time per request (default 120)
#   PREWARM_RADIUS_KM     default 8
#   PREWARM_DAYS          default 7
#   PREWARM_STRICT        if 1, exit non-zero when any batch fails
#   PREWARM_MAX_TERMS     cap how many terms to warm (default: all)
set -u

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
API_BASE="${API_BASE%/}"
BATCH_SIZE="${PREWARM_BATCH_SIZE:-1}"
DELAY="${PREWARM_DELAY:-1.5}"
TIMEOUT="${PREWARM_TIMEOUT:-120}"
RADIUS="${PREWARM_RADIUS_KM:-8}"
DAYS="${PREWARM_DAYS:-7}"
STRICT="${PREWARM_STRICT:-0}"
MAX_TERMS="${PREWARM_MAX_TERMS:-0}"

# Keep in sync with backend/app/services/sefaz/staples.py STAPLE_FETCH_TERMS
# (shell cannot import Python; intentional duplicate of the fetch list only).
TERMS=(
  arroz
  feijao
  leite
  acucar
  oleo
  pao
  cafe
  ovos
  macarrao
  manteiga
  sal
  "farinha de trigo"
  "molho de tomate"
  frango
  queijo
  banana
  tomate
  detergente
  "sabao em po"
  "papel higienico"
)

if [ "$MAX_TERMS" -gt 0 ] 2>/dev/null; then
  TERMS=("${TERMS[@]:0:$MAX_TERMS}")
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "prewarm-staples: curl missing — skip" >&2
  [ "$STRICT" = "1" ] && exit 1 || exit 0
fi

# Quick health gate — don't hammer a dead API.
if ! curl -fsS --max-time 5 "$API_BASE/health" >/dev/null 2>&1; then
  echo "prewarm-staples: $API_BASE/health not OK — skip" >&2
  [ "$STRICT" = "1" ] && exit 1 || exit 0
fi

echo "==> Staple prewarm via $API_BASE (batch=$BATCH_SIZE delay=${DELAY}s terms=${#TERMS[@]})"

ok=0
fail=0
n=${#TERMS[@]}
i=0
while [ "$i" -lt "$n" ]; do
  batch=()
  b=0
  while [ "$b" -lt "$BATCH_SIZE" ] && [ "$i" -lt "$n" ]; do
    batch+=("${TERMS[$i]}")
    i=$((i + 1))
    b=$((b + 1))
  done

  # Build JSON array of items safely (no shell injection via term content).
  json_items="["
  first=1
  for t in "${batch[@]}"; do
    # Escape backslash and double-quote for JSON string.
    esc=${t//\\/\\\\}
    esc=${esc//\"/\\\"}
    if [ "$first" -eq 1 ]; then
      json_items+="\"$esc\""
      first=0
    else
      json_items+=",\"$esc\""
    fi
  done
  json_items+="]"

  body=$(printf '{"items":%s,"latitude":-9.6633,"longitude":-35.7089,"radius_km":%s,"days":%s}' \
    "$json_items" "$RADIUS" "$DAYS")

  echo "  fetch: ${batch[*]}"
  code=$(curl -sS -o /tmp/prewarm_staples_body.$$ -w '%{http_code}' \
    --max-time "$TIMEOUT" \
    -H 'Content-Type: application/json' \
    -X POST "$API_BASE/api/v1/search" \
    -d "$body" || echo "000")
  rm -f /tmp/prewarm_staples_body.$$ 2>/dev/null || true

  if [ "$code" = "200" ]; then
    ok=$((ok + 1))
    echo "    status=200 ok"
  else
    fail=$((fail + 1))
    echo "    status=$code FAIL" >&2
  fi

  if [ "$i" -lt "$n" ] && [ "$(printf '%.0f' "$DELAY" 2>/dev/null || echo 1)" != "0" ]; then
    sleep "$DELAY" || true
  fi
done

echo "==> Staple prewarm done: ok_batches=$ok fail_batches=$fail"
if [ "$fail" -gt 0 ] && [ "$STRICT" = "1" ]; then
  exit 1
fi
exit 0
