# Security policy

## Supported versions

Only the **currently deployed** production stack at
`https://alagoas.precospublicos.ia.br` (and its admin/docs vhosts) is actively
maintained. Sideloaded or self-built APKs/web shells from arbitrary commits are
best-effort.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive reports.

1. Prefer email / contact listed in production
   [`/.well-known/security.txt`](https://alagoas.precospublicos.ia.br/.well-known/security.txt)
   (source: `deploy/well-known/security.txt` in this repo — operators must keep
   the live file in sync after deploy).
2. If that file is missing or outdated, open a **private** maintainer channel or
   a minimal public issue titled “security contact request” without exploit detail.
3. Include: affected host/version (`/health` `git_sha` if present), impact, and
   steps to reproduce. Avoid sending device tokens, admin tokens, or real user
   basket contents.

We aim to acknowledge within a reasonable maintainer timeframe; there is no
formal bug bounty.

## Scope notes

- The public **application API** is intentionally open for the Flutter/web client;
  rate limits and LGPD minimization apply, but it is not a private BFF.
- Admin (`admin.*`) is gated by a static `ADMIN_TOKEN` — treat it as a high-value
  secret (rotation, no commit, lock unattended consoles).
- `SECRET_ENCRYPTION_KEY` protects admin-stored secrets in Redis; see
  `docs/ops-secret-encryption-key-rotation.md` (#282).
- Do not commit `.env`, keystores, Play/App Store credentials, or real
  `assetlinks.json` / AASA fingerprints/TEAMID in PRs from untrusted forks.

## Hardening references in-repo

- `docs/seguranca-postura.html` / `docs/seguranca-e-dados.html` — posture & LGPD inventory
- `scripts/check_android_deploy_hardening.sh` — structural Android/deploy checks
- Issues/PRs tagged security, LGPD, or deploy/ops
