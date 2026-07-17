#!/usr/bin/env bash
# Sync SEFAZ_APP_TOKEN from CI (GitHub Actions secret) onto the VPS as a
# dedicated secret *file* — not into the shared .env.
#
# Layout on VPS (DEPLOY_DIR):
#   secrets/sefaz_app_token   # mode 600, dir 700 — Compose mounts as /run/secrets/…
#   .env                      # non-secret flags only; SEFAZ_APP_TOKEN cleared/empty
#
# Never prints the token. Streams it over scp into a short-lived incoming file,
# installs it under secrets/, hardens perms, flips USE_MOCK_SEFAZ / USE_WEB_SEFAZ
# in .env, and optionally recreates the API container.
#
# Required env:
#   SEFAZ_APP_TOKEN  — AppToken value (empty ⇒ no-op exit 0)
#   DEPLOY_HOST      — user@host
#   DEPLOY_DIR       — app dir on server (e.g. /srv/apps/alagoas)
# Optional:
#   DEPLOY_SSH_KEY_FILE — private key path (default: ~/.ssh/deploy_key)
#   RECREATE_API        — "1" (default) recreate api; "0" only write files
set -euo pipefail

if [ -z "${SEFAZ_APP_TOKEN:-}" ]; then
  echo "==> SEFAZ_APP_TOKEN secret empty — leaving VPS secrets/sefaz_app_token unchanged"
  exit 0
fi

: "${DEPLOY_HOST:?DEPLOY_HOST required}"
: "${DEPLOY_DIR:?DEPLOY_DIR required}"

KEY="${DEPLOY_SSH_KEY_FILE:-$HOME/.ssh/deploy_key}"
RECREATE_API="${RECREATE_API:-1}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes)
SCP=(scp -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes)

# Never log the token — length only.
echo "==> Syncing SEFAZ_APP_TOKEN → ${DEPLOY_HOST}:${DEPLOY_DIR}/secrets/sefaz_app_token (len=${#SEFAZ_APP_TOKEN}; value not logged)"

tmp="$(mktemp)"
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT
chmod 600 "$tmp"
# No trailing newline so the secret file is exact.
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
TOKEN_FILE="${SECRETS_DIR}/sefaz_app_token"

if [ ! -f "$ENV_FILE" ]; then
  echo "ABORT: ${ENV_FILE} missing (create it on the server first; secrets never ship from git)." >&2
  rm -f "$IN"
  exit 1
fi
if [ ! -f "$IN" ]; then
  echo "ABORT: missing incoming token file." >&2
  exit 1
fi

mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Install token file atomically (mode 600).
install -m 600 /dev/null "${TOKEN_FILE}.tmp" 2>/dev/null || {
  : > "${TOKEN_FILE}.tmp"
  chmod 600 "${TOKEN_FILE}.tmp"
}
cat "$IN" > "${TOKEN_FILE}.tmp"
chmod 600 "${TOKEN_FILE}.tmp"
mv -f "${TOKEN_FILE}.tmp" "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"

# Shred incoming (best-effort).
if command -v shred >/dev/null 2>&1; then
  shred -u "$IN" 2>/dev/null || rm -f "$IN"
else
  rm -f "$IN"
fi

# Flags in .env only — clear any leftover SEFAZ_APP_TOKEN so the token is not
# duplicated in the shared env file (Compose uses SEFAZ_APP_TOKEN_FILE).
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
# Empty string — token lives in secrets/sefaz_app_token only.
updated = upsert(updated, "SEFAZ_APP_TOKEN", "")

mode = env_path.stat().st_mode & 0o777
fd, tmp_name = tempfile.mkstemp(
    dir=str(env_path.parent), prefix=".env.", suffix=".tmp"
)
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

print("OK: secrets/sefaz_app_token installed; .env flags USE_MOCK_SEFAZ=false USE_WEB_SEFAZ=false; SEFAZ_APP_TOKEN cleared")
PY

if [ "${RECREATE_API}" = "1" ]; then
  cd "${DEPLOY_DIR}/deploy"
  if docker compose --env-file ../.env ps -q api 2>/dev/null | grep -q .; then
    echo "==> Recreating api container to mount updated secret file"
    docker compose --env-file ../.env up -d --no-build --force-recreate api
    for i in 1 2 3 4 5 6; do
      if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "==> API healthy after token sync"
        exit 0
      fi
      sleep 5
    done
    echo "WARN: API not healthy yet after recreate (deploy job may still be bringing stack up)." >&2
  else
    echo "==> api not running yet; secret file ready — next compose up will mount it"
  fi
fi
REMOTE
