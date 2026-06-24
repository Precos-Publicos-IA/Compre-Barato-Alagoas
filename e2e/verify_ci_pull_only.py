#!/usr/bin/env python3
"""Assert deploy.yml is pull-only for the CI toolchain (job container.image).

Fails if deploy.yml builds e2e/Dockerfile.ci or save/loads a ci-e2e artifact.
VPS app `docker save` of API_IMAGE is allowed. Run from repo root:
  python3 e2e/verify_ci_pull_only.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
CI_IMG = (ROOT / ".github/workflows/ci-image.yml").read_text(encoding="utf-8")

errors: list[str] = []

# Consumers must use container + CI_E2E_IMAGE
for job in ("test", "e2e-local", "live-verify"):
    m = re.search(rf"\n  {job}:\n(?P<body>.*?)(?=\n  [a-z].*:|\Z)", DEPLOY, re.S)
    if not m:
        errors.append(f"missing job {job}")
        continue
    body = m.group("body")
    if "container:" not in body or "CI_E2E_IMAGE" not in body:
        errors.append(f"{job}: must set container.image from CI_E2E_IMAGE")

if "CI_E2E_IMAGE: ghcr.io/precos-publicos-ia/compre-barato-alagoas/ci-e2e:latest" not in DEPLOY:
    errors.append("CI_E2E_IMAGE must be lowercase GHCR path …/ci-e2e:latest")

# No toolchain build in deploy (ignore comments)
code_lines = [ln for ln in DEPLOY.splitlines() if not ln.lstrip().startswith("#")]
code = "\n".join(code_lines)
if re.search(r"Dockerfile\.ci", code):
    errors.append("deploy.yml must not reference Dockerfile.ci outside comments")
if re.search(r"ci-e2e\.tar", code) or re.search(r"name:\s*ci-e2e-image", code):
    errors.append("deploy.yml must not save/load ci-e2e image artifacts")
if re.search(r"docker buildx build.*ci-e2e|buildx build[^\n]*Dockerfile\.ci", code):
    errors.append("deploy.yml must not buildx-build the CI toolchain image")

# Publisher: no PR trigger in on: block
on_block = CI_IMG.split("jobs:")[0]
if "pull_request:" in on_block:
    errors.append("ci-image.yml must not publish on pull_request")
if "workflow_dispatch:" not in on_block:
    errors.append("ci-image.yml should allow workflow_dispatch")
if "schedule:" not in on_block:
    errors.append("ci-image.yml should allow schedule")

if errors:
    print("FAIL verify_ci_pull_only:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("PASS verify_ci_pull_only: deploy consumers are pull-only; ci-image is sole publisher pattern")
sys.exit(0)
