#!/usr/bin/env bash
# Sync SEFAZ_APP_TOKEN from CI (GitHub Actions secret) into the VPS .env.
#
# Runs on the GHA runner (or any machine with SSH access). Never prints the
# token. Streams it over scp into a short-lived file on the VPS, merges into
# .env, shreds the temp file, and recreates the API container so compose reloads
# env_file.
#
# Required env:
#   SEFAZ_APP_TOKEN  — AppToken value (empty ⇒ no-op exit 0)
#   DEPLOY_HOST      — user@host
#   DEPLOY_DIR       — app dir on server (e.g. /srv/apps/alagoas)
# Optional:
#   DEPLOY_SSH_KEY_FILE — private key path (default: ~/.ssh/deploy_key)
#   RECREATE_API        — "1" (default) recreate api; "0" only write .env
set -euo pipefail

if [ -z "${SEFAZ_APP_TOKEN:-}" ]; then
  echo "==> SEFAZ_APP_TOKEN secret empty — leaving VPS .env SEFAZ keys unchanged"
  exit 0
fi

: "${DEPLOY_HOST:?DEPLOY_HOST required}"
: "${DEPLOY_DIR:?DEPLOY_DIR required}"

KEY="${DEPLOY_SSH_KEY_FILE:-$HOME/.ssh/deploy_key}"
RECREATE_API="${RECREATE_API:-1}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes)
SCP=(scp -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes)

# Never log the token — length only (helps catch accidental empty/whitespace).
echo "==> Syncing SEFAZ_APP_TOKEN to ${DEPLOY_HOST}:${DEPLOY_DIR}/.env (len=${#SEFAZ_APP_TOKEN}; value not logged)"

tmp="$(mktemp)"
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT
chmod 600 "$tmp"
# No trailing newline so .env value is exact.
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

if [ ! -f "$ENV_FILE" ]; then
  echo "ABORT: ${ENV_FILE} missing (create it on the server first; secrets never ship from git)." >&2
  rm -f "$IN"
  exit 1
fi
if [ ! -f "$IN" ]; then
  echo "ABORT: missing incoming token file." >&2
  exit 1
fi

export ENV_FILE IN
python3 <<'PY'
import os
import pathlib
import re
import tempfile

env_path = pathlib.Path(os.environ["ENV_FILE"])
token = pathlib.Path(os.environ["IN"]).read_bytes()
# Decode as utf-8; SEFAZ tokens are typically ASCII.
try:
    token_s = token.decode("utf-8")
except UnicodeDecodeError as e:
    raise SystemExit(f"ABORT: token is not valid UTF-8: {e}") from e
if not token_s.strip():
    raise SystemExit("ABORT: token file empty")

def quote_env(value: str) -> str:
    """Safe double-quoted .env value (docker compose / dotenv)."""
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'

def upsert(text: str, key: str, value: str) -> str:
    line = f"{key}={quote_env(value)}"
    # Replace the entire KEY=... line (not only the key prefix).
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"

raw = env_path.read_text(encoding="utf-8")
updated = upsert(raw, "SEFAZ_APP_TOKEN", token_s)
updated = upsert(updated, "USE_MOCK_SEFAZ", "false")
# Prefer official JSON API once a token is present (operator can still flip).
updated = upsert(updated, "USE_WEB_SEFAZ", "false")

# Atomic replace; keep mode (prefer 600).
mode = env_path.stat().st_mode & 0o777
fd, tmp_name = tempfile.mkstemp(
    dir=str(env_path.parent), prefix=".env.", suffix=".tmp"
)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(updated)
    os.chmod(tmp_name, mode or 0o600)
    os.replace(tmp_name, env_path)
finally:
    try:
        os.unlink(tmp_name)
    except FileNotFoundError:
        pass

print("OK: upserted SEFAZ_APP_TOKEN, USE_MOCK_SEFAZ=false, USE_WEB_SEFAZ=false")
PY

# Shred incoming token file (best-effort).
if command -v shred >/dev/null 2>&1; then
  shred -u "$IN" 2>/dev/null || rm -f "$IN"
else
  rm -f "$IN"
fi

if [ "${RECREATE_API}" = "1" ]; then
  cd "${DEPLOY_DIR}/deploy"
  if docker compose --env-file ../.env ps -q api 2>/dev/null | grep -q .; then
    echo "==> Recreating api container to load new env_file"
    docker compose --env-file ../.env up -d --no-build --force-recreate api
    # Brief health wait (remote-update does a fuller check when used).
    for i in 1 2 3 4 5 6; do
      if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "==> API healthy after token sync"
        exit 0
      fi
      sleep 5
    done
    echo "WARN: API not healthy yet after recreate (deploy job may still be bringing stack up)." >&2
  else
    echo "==> api not running yet; .env updated — next compose up will pick up the token"
  fi
fi
REMOTE
