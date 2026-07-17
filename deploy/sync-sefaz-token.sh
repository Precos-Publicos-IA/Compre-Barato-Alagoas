#!/usr/bin/env bash
# Sync SEFAZ_APP_TOKEN from CI (GitHub Actions secret) onto the VPS.
#
# Why secrets/sefaz.env (not a mode-600 bind mount alone):
#   The API container runs as non-root appuser (uid 10001). A host file with
#   mode 600 bind-mounted as a Compose "secret" is unreadable inside the
#   container → token empty → website scrape fallback → flaky live search.
#   Compose env_file is read on the *host* by the deploy user and injected as
#   process env, so non-root can use the token without world-readable files.
#
# Layout on VPS (DEPLOY_DIR):
#   secrets/sefaz.env         # mode 600, only SEFAZ_APP_TOKEN=… (Compose env_file)
#   secrets/sefaz_app_token   # mode 644 raw token (optional FILE fallback)
#   .env                      # non-secret flags; SEFAZ_APP_TOKEN cleared
#
# Never prints the token.
#
# Required env: SEFAZ_APP_TOKEN, DEPLOY_HOST, DEPLOY_DIR
# Optional: DEPLOY_SSH_KEY_FILE, RECREATE_API (default 1)
set -euo pipefail

if [ -z "${SEFAZ_APP_TOKEN:-}" ]; then
  echo "==> SEFAZ_APP_TOKEN secret empty — leaving VPS secrets/ unchanged"
  exit 0
fi

: "${DEPLOY_HOST:?DEPLOY_HOST required}"
: "${DEPLOY_DIR:?DEPLOY_DIR required}"

KEY="${DEPLOY_SSH_KEY_FILE:-$HOME/.ssh/deploy_key}"
RECREATE_API="${RECREATE_API:-1}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes)
SCP=(scp -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes)

echo "==> Syncing SEFAZ_APP_TOKEN → ${DEPLOY_HOST}:${DEPLOY_DIR}/secrets/ (len=${#SEFAZ_APP_TOKEN}; value not logged)"

tmp="$(mktemp)"
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT
chmod 600 "$tmp"
printf '%s' "$SEFAZ_APP_TOKEN" > "$tmp"

remote_incoming="${DEPLOY_DIR}/.sefaz_app_token.incoming"
"${SCP[@]}" "$tmp" "${DEPLOY_HOST}:${remote_incoming}"
rm -f "$tmp"
trap - EXIT

"${SSH[@]}" "$DEPLOY_HOST" \
  "DEPLOY_DIR=$(printf %q "$DEPLOY_DIR") RECREATE_API=$(printf %q "$RECREATE_API") bash -s" <<'REMOTE'
set -euo pipefail
umask 077

IN="${DEPLOY_DIR}/.sefaz_app_token.incoming"
ENV_FILE="${DEPLOY_DIR}/.env"
SECRETS_DIR="${DEPLOY_DIR}/secrets"
TOKEN_RAW="${SECRETS_DIR}/sefaz_app_token"
TOKEN_ENV="${SECRETS_DIR}/sefaz.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ABORT: ${ENV_FILE} missing (create it on the server first)." >&2
  rm -f "$IN"
  exit 1
fi
if [ ! -f "$IN" ]; then
  echo "ABORT: missing incoming token file." >&2
  exit 1
fi

mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

TOKEN=$(cat "$IN")
if [ -z "${TOKEN// }" ]; then
  echo "ABORT: token empty after transfer." >&2
  rm -f "$IN"
  exit 1
fi

# 1) Raw file for SEFAZ_APP_TOKEN_FILE fallback. Mode 644 so non-root appuser
#    can read a bind mount (host multi-user risk is low on a dedicated VPS).
umask 022
printf '%s' "$TOKEN" > "${TOKEN_RAW}.tmp"
chmod 644 "${TOKEN_RAW}.tmp"
mv -f "${TOKEN_RAW}.tmp" "$TOKEN_RAW"
chmod 644 "$TOKEN_RAW"

# 2) env_file fragment — primary path (compose injects into container env).
export TOKEN TOKEN_ENV
python3 <<'PY'
import os
import pathlib
import tempfile

token = os.environ["TOKEN"]
path = pathlib.Path(os.environ["TOKEN_ENV"])

def quote_env(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'

body = (
    "# Managed by deploy/sync-sefaz-token.sh — never commit\n"
    f"SEFAZ_APP_TOKEN={quote_env(token)}\n"
)
fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix="sefaz.env.", suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(tmp_name, 0o600)
    os.replace(tmp_name, path)
    os.chmod(path, 0o600)
finally:
    try:
        os.unlink(tmp_name)
    except FileNotFoundError:
        pass
print(f"OK: wrote {path} (mode 600) and sefaz_app_token (mode 644 for FILE fallback)")
PY

# Shred incoming
if command -v shred >/dev/null 2>&1; then
  shred -u "$IN" 2>/dev/null || rm -f "$IN"
else
  rm -f "$IN"
fi

# Flags only in shared .env — clear any leftover SEFAZ_APP_TOKEN there.
export ENV_FILE
python3 <<'PY'
import os
import pathlib
import re
import tempfile

env_path = pathlib.Path(os.environ["ENV_FILE"])

def quote_env(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'

def upsert(text: str, key: str, value: str) -> str:
    line = f"{key}={quote_env(value)}"
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"

raw = env_path.read_text(encoding="utf-8")
updated = upsert(raw, "USE_MOCK_SEFAZ", "false")
updated = upsert(updated, "USE_WEB_SEFAZ", "false")
updated = upsert(updated, "SEFAZ_APP_TOKEN", "")

mode = env_path.stat().st_mode & 0o777
fd, tmp_name = tempfile.mkstemp(dir=str(env_path.parent), prefix=".env.", suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(updated)
    os.chmod(tmp_name, mode or 0o600)
    os.replace(tmp_name, env_path)
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass
finally:
    try:
        os.unlink(tmp_name)
    except FileNotFoundError:
        pass
print("OK: .env USE_MOCK_SEFAZ=false USE_WEB_SEFAZ=false; SEFAZ_APP_TOKEN cleared from shared .env")
PY

if [ "${RECREATE_API}" = "1" ]; then
  cd "${DEPLOY_DIR}/deploy"
  if docker compose --env-file ../.env ps -q api 2>/dev/null | grep -q .; then
    echo "==> Recreating api container to load new secrets env_file"
    # Pass both env files explicitly (compose also lists them).
    docker compose --env-file ../.env --env-file ../secrets/sefaz.env \
      up -d --no-build --force-recreate api
    for i in 1 2 3 4 5 6; do
      if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "==> API healthy after token sync"
        exit 0
      fi
      sleep 5
    done
    echo "WARN: API not healthy yet after recreate." >&2
  else
    echo "==> api not running yet; secrets ready — next compose up will load them"
  fi
fi
REMOTE
