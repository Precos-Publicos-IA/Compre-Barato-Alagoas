#!/usr/bin/env bash
# Runs ON the VPS to (re)start the stack with an already-present API image.
# The CI pipeline builds the image elsewhere and loads it onto the host, then
# calls this script over SSH. Nothing here builds images, so no build cache
# accumulates on the (shared) server.
#
#   API_IMAGE   tag of the API image to run   (e.g. compre-barato-alagoas-api:<sha>)
#   DEPLOY_DIR  app directory on the server    (default: /srv/apps/compre-barato-alagoas)
#   MIN_FREE_MB minimum free disk to proceed   (default: 2048)
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/srv/apps/compre-barato-alagoas}"
API_IMAGE="${API_IMAGE:-compre-barato-alagoas-api:latest}"
MIN_FREE_MB="${MIN_FREE_MB:-2048}"

# --- Disk pre-check: never risk filling a shared host. ---
avail_mb=$(($(df -Pk "$DEPLOY_DIR" | awk 'NR==2{print $4}') / 1024))
echo "==> Free disk at $DEPLOY_DIR: ${avail_mb}MB (need >= ${MIN_FREE_MB}MB)"
if [ "$avail_mb" -lt "$MIN_FREE_MB" ]; then
  echo "ABORT: not enough free disk. Deployment stopped before touching the stack." >&2
  exit 1
fi

if [ ! -f "$DEPLOY_DIR/.env" ]; then
  echo "ABORT: $DEPLOY_DIR/.env is missing (config lives only on the server)." >&2
  exit 1
fi

# SEFAZ AppToken lives under secrets/ (see sync-sefaz-token.sh + docker-compose).
# Ensure files exist so compose env_file / bind never fail (empty = no token → web).
mkdir -p "$DEPLOY_DIR/secrets"
chmod 700 "$DEPLOY_DIR/secrets"
if [ ! -f "$DEPLOY_DIR/secrets/sefaz.env" ]; then
  umask 077
  printf '%s\n' '# Managed by deploy — set via GitHub SEFAZ_APP_TOKEN' 'SEFAZ_APP_TOKEN=' \
    > "$DEPLOY_DIR/secrets/sefaz.env"
  chmod 600 "$DEPLOY_DIR/secrets/sefaz.env"
  echo "==> Created empty secrets/sefaz.env (set GitHub secret SEFAZ_APP_TOKEN to fill)"
else
  chmod 600 "$DEPLOY_DIR/secrets/sefaz.env" 2>/dev/null || true
fi
if [ ! -f "$DEPLOY_DIR/secrets/sefaz_app_token" ]; then
  : > "$DEPLOY_DIR/secrets/sefaz_app_token"
  chmod 644 "$DEPLOY_DIR/secrets/sefaz_app_token"
  echo "==> Created empty secrets/sefaz_app_token (FILE fallback)"
else
  # Keep world-readable for non-root appuser bind mount (token also in sefaz.env).
  chmod 644 "$DEPLOY_DIR/secrets/sefaz_app_token" 2>/dev/null || true
fi
chmod 600 "$DEPLOY_DIR/.env" 2>/dev/null || true

cd "$DEPLOY_DIR/deploy"

# Never start with a missing tag. Bare :latest is only OK if that image exists
# locally (manual compose); CI pins sha tags and often has no :latest.
if [ -z "${API_IMAGE:-}" ]; then
  echo "ABORT: API_IMAGE is empty (refuse default :latest when unset)." >&2
  exit 1
fi
if ! docker image inspect "$API_IMAGE" >/dev/null 2>&1; then
  echo "ABORT: API image not present on host: $API_IMAGE" >&2
  echo "       Load a built image or pass a tag that exists (docker images compre-barato-alagoas-api)." >&2
  exit 1
fi
export API_IMAGE

echo "==> Starting stack with API_IMAGE=$API_IMAGE"
# No --build: the image is already loaded on the host.
docker compose --env-file ../.env --env-file ../secrets/sefaz.env up -d --no-build

# Remove our own previous API images so per-commit tags don't pile up. Scoped
# strictly to this app's repository name, so other clients' images are never
# touched; the image we just deployed is kept.
echo "==> Removing older compre-barato-alagoas-api images (keep $API_IMAGE)"
docker images 'compre-barato-alagoas-api' --format '{{.Repository}}:{{.Tag}}' \
  | grep -vx "$API_IMAGE" \
  | xargs -r docker rmi -f >/dev/null 2>&1 || true
# Drop any now-dangling layers (own leftovers only; never touches running refs).
docker image prune -f >/dev/null 2>&1 || true

echo "==> Health check"
for i in 1 2 3 4 5 6; do
  if curl -fsS http://127.0.0.1:8000/health; then echo; echo "==> Healthy."; exit 0; fi
  echo "   …waiting for API ($i/6)"; sleep 5
done
echo "ABORT: API did not become healthy." >&2
exit 1
