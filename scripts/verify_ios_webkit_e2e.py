#!/usr/bin/env python3
"""iOS/WebKit e2e readiness checks (issue #16).

Headless e2e uses Puppeteer/Chrome with a mobile viewport — not Safari/WebKit.
This script enforces documentation of that gap, a manual iPhone checklist template,
and that the iOS scaffold is in-scope once declared.

No macOS/Xcode/Playwright required. Run from repo root:
  python3 scripts/verify_ios_webkit_e2e.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E_README = ROOT / "e2e/README.md"
AGENTS = ROOT / "AGENTS.md"
TEMPLATE = ROOT / ".github/ISSUE_TEMPLATE/iphone-safari-checklist.md"
IOS_README = ROOT / "frontend/ios/README.md"
IOS_PLIST = ROOT / "frontend/ios/Runner/Info.plist"
FULL_JS = ROOT / "e2e/full.js"
SMOKE_JS = ROOT / "e2e/smoke.js"

errors: list[str] = []
warnings: list[str] = []


def _read(p: Path) -> str:
    if not p.is_file():
        errors.append(f"missing {p.relative_to(ROOT)}")
        return ""
    return p.read_text(encoding="utf-8")


e2e_readme = _read(E2E_README)
agents = _read(AGENTS)
template = _read(TEMPLATE)
_ = _read(IOS_README)

# --- Docs must acknowledge Chromium-only mobile e2e (#16) ---
for label, body, needles in (
    ("e2e/README.md", e2e_readme, ("WebKit", "Safari", "Chromium", "iPhone")),
    ("AGENTS.md", agents, ("WebKit", "Safari", "Chromium")),
):
    if not body:
        continue
    missing = [n for n in needles if n not in body]
    if missing:
        errors.append(
            f"{label} must document iOS/WebKit limitation; missing: {', '.join(missing)}"
        )

# --- Issue template for manual iPhone Safari QA ---
if template:
    tl = template.lower()
    for needle in ("safe-area", "add to home screen", "font-size", "webkit", "iphone"):
        if needle not in tl:
            errors.append(f"iphone-safari-checklist.md missing guidance on: {needle}")

# --- iOS declared in-scope: scaffold must exist ---
if not IOS_README.is_file() and not IOS_PLIST.is_file():
    errors.append(
        "frontend/ios/ missing — iOS is in-scope; add at least ios/README.md scaffold "
        "(or full flutter create on Mac — issues #4/#5/#10)"
    )
elif IOS_README.is_file() and not IOS_PLIST.is_file():
    warnings.append(
        "frontend/ios/README.md present but Runner/Info.plist missing "
        "(privacy/queries may land via #5/#10 PR)"
    )

# --- e2e still uses Chromium mobile viewport (sanity) ---
for label, p in (("e2e/full.js", FULL_JS), ("e2e/smoke.js", SMOKE_JS)):
    if not p.is_file():
        errors.append(f"missing {p.relative_to(ROOT)}")
        continue
    t = p.read_text(encoding="utf-8")
    if "isMobile: true" not in t and "isMobile:true" not in t:
        warnings.append(
            f"{label}: no isMobile:true viewport (ok if WebKit job added elsewhere)"
        )
    _ = re  # keep import used if we extend later

if warnings:
    print("WARN verify_ios_webkit_e2e:")
    for w in warnings:
        print(" -", w)

if errors:
    print("FAIL verify_ios_webkit_e2e:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print(
    "PASS verify_ios_webkit_e2e: WebKit limitation documented, "
    "iPhone checklist template present, iOS scaffold in-scope"
)
sys.exit(0)
