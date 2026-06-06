#!/usr/bin/env bash
# Build + ship + (re)start Compre Barato Alagoas on a server.
# Usage: ./deploy.sh   (run from the deploy/ directory or repo root)
#
# Configure the target via environment variables (nothing host-specific is committed):
#   DEPLOY_HOST     user@host of the server         (e.g. deploy@your-server.example.com)
#   DEPLOY_SSH_KEY  path to the SSH private key      (default: ~/.ssh/id_ed25519)
#   DEPLOY_DOMAIN   public domain served by nginx    (default: the production domain)
#   DEPLOY_DIR      app directory on the server       (default: /srv/apps/compre-barato-alagoas)
set -euo pipefail

HOST="${DEPLOY_HOST:-deploy@your-server.example.com}"
SSH_KEY="${DEPLOY_SSH_KEY:-$HOME/.ssh/id_ed25519}"
DOMAIN="${DEPLOY_DOMAIN:-alagoas.precospublicos.ia.br}"
REMOTE_DIR="${DEPLOY_DIR:-/srv/apps/compre-barato-alagoas}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SSH=(ssh -i "$SSH_KEY" "$HOST")
RSYNC_RSH="ssh -i $SSH_KEY"

echo "==> Building Flutter web + release APK (API_BASE_URL=https://$DOMAIN)"
( cd "$REPO_DIR/frontend" && flutter build web --release \
    --dart-define=API_BASE_URL="https://$DOMAIN" )
( cd "$REPO_DIR/frontend" && flutter build apk --release \
    --dart-define=API_BASE_URL="https://$DOMAIN" )

echo "==> Ensuring remote dir"
"${SSH[@]}" "mkdir -p $REMOTE_DIR/web $REMOTE_DIR/admin $REMOTE_DIR/docs"

echo "==> Syncing backend + deploy + .env.example + web"
# Never sync a real .env (secrets stay on the server).
rsync -az --delete -e "$RSYNC_RSH" \
  --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude '.env' \
  "$REPO_DIR/backend" "$REPO_DIR/deploy" "$HOST:$REMOTE_DIR/"
rsync -az -e "$RSYNC_RSH" "$REPO_DIR/.env.example" "$HOST:$REMOTE_DIR/.env.example"
# Never delete web/app (the hosted APK lives there, not in the web build).
rsync -az --delete -e "$RSYNC_RSH" --exclude 'app/' \
  "$REPO_DIR/frontend/build/web/" "$HOST:$REMOTE_DIR/web/"
"${SSH[@]}" "mkdir -p $REMOTE_DIR/web/app"
rsync -az -e "$RSYNC_RSH" \
  "$REPO_DIR/frontend/build/app/outputs/flutter-apk/app-release.apk" \
  "$HOST:$REMOTE_DIR/web/app/compre-barato-alagoas.apk"

echo "==> Syncing admin dashboard (static; served at admin.$DOMAIN)"
rsync -az --delete -e "$RSYNC_RSH" \
  "$REPO_DIR/admin-frontend/" "$HOST:$REMOTE_DIR/admin/"

echo "==> Syncing docs site (static; served at docs.$DOMAIN)"
rsync -az --delete -e "$RSYNC_RSH" \
  "$REPO_DIR/docs/" "$HOST:$REMOTE_DIR/docs/"

echo "==> Building & starting containers (single .env at $REMOTE_DIR/.env)"
"${SSH[@]}" "cd $REMOTE_DIR && [ -f .env ] || cp .env.example .env; \
  cd deploy && docker compose --env-file ../.env up -d --build"

echo "==> Health check"
"${SSH[@]}" "sleep 5 && curl -fsS http://127.0.0.1:8000/health && echo"

echo "==> Done. If first deploy, install the nginx vhost + certbot (see deploy/README.md)."
