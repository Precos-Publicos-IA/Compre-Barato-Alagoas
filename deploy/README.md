# Deploy — Compre Barato Alagoas

Deploys the project on a Linux server with Docker, behind **nginx + certbot** that
already handles TLS. Nothing host-specific is committed: host, user, SSH key, and
directory are passed via environment variables; secrets live in a single `.env`.

## Topology

```
Internet → host nginx (TLS, certbot)
            ├── /                → static Flutter web at <DEPLOY_DIR>/web
            └── /api,/health,... → reverse proxy 127.0.0.1:8000 (Docker)
Docker (compose, deploy/):
   api (FastAPI, 127.0.0.1:8000) · postgres (pgvector) · redis
```

Only the API port is published, and only on `localhost`.

## Configuration

All configuration lives in **a single `.env` at the repository root** (copy from
`.env.example`). It feeds both the backend and `docker-compose`. The `.env` is
**never** committed or shipped by deploy — it stays only on the server.

The deploy target is set via environment variables when running `deploy.sh`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEPLOY_HOST` | `user@host` of the server | `deploy@your-server.example.com` |
| `DEPLOY_SSH_KEY` | path to the SSH private key | `~/.ssh/id_ed25519` |
| `DEPLOY_DOMAIN` | public domain served by nginx | production domain |
| `DEPLOY_DIR` | app directory on the server | `/srv/apps/compre-barato-alagoas` |

## First deploy

From a machine with the repository and Flutter installed:

```bash
# 1) Ship code + builds and create the containers.
DEPLOY_HOST=user@YOUR_SERVER \
DEPLOY_SSH_KEY=~/.ssh/your_key \
DEPLOY_DIR=/srv/apps/compre-barato-alagoas \
  deploy/deploy.sh

# 2) On the server, set secrets in .env (at the root of DEPLOY_DIR).
ssh -i ~/.ssh/your_key user@YOUR_SERVER
cd /srv/apps/compre-barato-alagoas
nano .env       # set POSTGRES_PASSWORD; keep USE_MOCK_* = true for now
cd deploy && docker compose --env-file ../.env up -d
curl -s http://127.0.0.1:8000/health    # expect status ok

# 3) Configure the nginx vhost + TLS (a new vhost; other sites stay untouched).
sudo cp deploy/nginx/alagoas.precospublicos.ia.br.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/alagoas.precospublicos.ia.br.conf \
           /etc/nginx/sites-enabled/
#   Point the vhost `root` at <DEPLOY_DIR>/web.
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR_DOMAIN      # issue and install the certificate

# 4) Final test.
curl -s https://YOUR_DOMAIN/health
```

## CI/CD (auto-deploy on every push to `main`)

The `.github/workflows/deploy.yml` workflow auto-deploys on every push to
`main`, but **only what actually changed** (`changes` job detects paths):

| What changed… | What the pipeline does |
|---------------|------------------------|
| `backend/**` | runs `pytest`, rebuilds the image, restarts the stack |
| `frontend/**` | rebuilds Flutter web + APK and syncs (no API restart) |
| `deploy/**`, `.env.example`, the workflow itself | syncs and restarts the stack with the current image |
| `admin-frontend/**` | only syncs the dashboard (no rebuild/restart) |
| `docs/**` | only syncs the docs site (no rebuild/restart) |
| only `README.md` / `LICENSE` / `.gitignore` / `shared-assets/**` | **nothing** — pipeline does not start |

Deploy details when there is code:
- the backend image (lean multi-stage Dockerfile) is built **on the runner**,
  never on the server — no build cache piles up on the shared host;
- ship over SSH: image via `docker save | docker load` (no registry), statics via `rsync`;
- before touching the host there is a **disk check** (aborts if < ~2 GB free);
  `deploy/remote-update.sh` brings the stack up, removes old images **for this app only**, and runs a health check.
- `workflow_dispatch` (Run workflow) forces a full deploy — useful for redeploy/rollback.

Configure repository *secrets* once (nothing host-specific is committed):

| Secret | Contents |
|--------|----------|
| `DEPLOY_HOST` | `user@host` of the server |
| `DEPLOY_SSH_KEY` | deploy **private** SSH key (file contents) |
| `DEPLOY_DIR` | app directory on the server |
| `DEPLOY_DOMAIN` | public domain (used in the Flutter build) |

Host nginx/TLS is **not** touched by the pipeline (still managed by hand on the server).
To run manually without a push, use **Actions → this workflow → Run workflow**.

## Manual updates (fallback)

`deploy.sh` rebuilds web + APK, syncs backend/deploy/web, and recreates containers
**building the image on the server itself**. That is the emergency path; normally the
CI/CD above owns deploy. Run it with the same environment variables as the first deploy.

## Going live with real data

Edit `.env` on the server:

```
USE_MOCK_SEFAZ=false
# Leave empty to scrape the public Economiza website (tokenless fallback).
# When SEFAZ issues an AppToken, set it here or via the admin Settings panel.
SEFAZ_APP_TOKEN=
USE_MOCK_LLM=false
ANTHROPIC_API_KEY=<key>
# Website scrape is slow — keep concurrency low (defaults are already conservative).
SEFAZ_WEB_CONCURRENCY=2
SEFAZ_CONCURRENCY=3
```

then `cd deploy && docker compose --env-file ../.env up -d` to restart the API.
No code changes are required. Health (`/health`) reports `data_source` as `web`
or `sefaz` depending on whether a token is active.

## Notes

- The deploy user must be in the `docker` group to run `docker compose` without
  `sudo`.
- On a shared host, **never** use `docker system prune`. Clean only your own
  images: `docker image prune -f` / `docker builder prune -f`.
