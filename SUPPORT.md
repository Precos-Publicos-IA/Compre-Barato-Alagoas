# Support

## End users (shoppers)

- **App / web:** https://alagoas.precospublicos.ia.br  
- **Privacy policy (in-app / web):** `/privacy.html` on the app host and LGPD pages under the docs site.  
- **How it works / API overview:** https://docs.alagoas.precospublicos.ia.br  
- There is **no account login**; optional device consent stores lists on the server. Use in-app settings to turn off anonymous usage stats or withdraw consent / delete device data where implemented.

If search fails, note approximate time, whether you used voice/location, and any **código de referência** (`ref:` / request id) shown with the error if your build surfaces it (#273 tracks better UX).

## Titular rights / LGPD process

Technical capabilities (consent, device delete, hashed analytics) are described in `docs/seguranca-e-dados.html` and `docs/lgpd-medicao-de-uso.html`. A dedicated DPO/encarregado contact and titular request form are tracked in issue **#276** — until then, use the contact in production `/.well-known/security.txt` / [`SECURITY.md`](SECURITY.md) for privacy requests, including device-token context only through secure channels.

## Operators / deployers

- Deploy: `deploy/README.md`
- Image/supply-chain notes: image pinning section in `deploy/README.md` (#269)
- Secret encryption key rotation: `docs/ops-secret-encryption-key-rotation.md` (#282)
- Policy version bumps: `docs/ops-policy-version-release.md` (#283)
- Android App Links placeholders: `deploy/well-known/README.md` (#257)
- Uptime/status page: not yet (#249)

## Contributors / developers

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`AGENTS.md`](AGENTS.md) — agent/PR workflow
- [`CHANGELOG.md`](CHANGELOG.md) — notable changes
- GitHub Issues / Pull Requests on this repository

## What we do not provide

- Guaranteed SLA or 24/7 on-call
- Support for arbitrary third-party forks or modified binaries
- SEFAZ-AL operational support (upstream government API)
