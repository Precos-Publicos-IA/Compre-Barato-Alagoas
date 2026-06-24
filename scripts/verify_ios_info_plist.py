#!/usr/bin/env python3
"""Structural checks for iOS Info.plist privacy + LSApplicationQueriesSchemes.

Does not require macOS/Xcode/Flutter. Run from repo root:
  python3 scripts/verify_ios_info_plist.py

Covers issues #5 (privacy usage strings) and #10 (URL scheme queries).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLIST = ROOT / "frontend/ios/Runner/Info.plist"
STRINGS = ROOT / "frontend/ios/Runner/InfoPlist.strings"
README = ROOT / "frontend/ios/README.md"

errors: list[str] = []

if not PLIST.is_file():
    errors.append(f"missing {PLIST.relative_to(ROOT)}")
    print("FAIL verify_ios_info_plist:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

text = PLIST.read_text(encoding="utf-8")

# --- #5 privacy keys ---
privacy_keys = (
    "NSMicrophoneUsageDescription",
    "NSSpeechRecognitionUsageDescription",
    "NSLocationWhenInUseUsageDescription",
)
for key in privacy_keys:
    if f"<key>{key}</key>" not in text:
        errors.append(f"Info.plist missing key {key}")
    else:
        # Require a non-empty <string> value after the key (simple line-oriented check)
        m = re.search(
            rf"<key>{re.escape(key)}</key>\s*<string>([^<]*)</string>",
            text,
            re.S,
        )
        if not m or not m.group(1).strip():
            errors.append(f"Info.plist {key} must have a non-empty <string> value")
        elif len(m.group(1).strip()) < 12:
            errors.append(f"Info.plist {key} value looks too short for App Store review")

# --- #10 LSApplicationQueriesSchemes ---
if "<key>LSApplicationQueriesSchemes</key>" not in text:
    errors.append("Info.plist missing LSApplicationQueriesSchemes")
else:
    required_schemes = ("uber", "taxis99", "99app", "comgooglemaps", "maps")
    # Extract the first array after LSApplicationQueriesSchemes
    m = re.search(
        r"<key>LSApplicationQueriesSchemes</key>\s*<array>(.*?)</array>",
        text,
        re.S,
    )
    if not m:
        errors.append("LSApplicationQueriesSchemes must be followed by an <array>")
    else:
        block = m.group(1)
        for scheme in required_schemes:
            if f"<string>{scheme}</string>" not in block:
                errors.append(f"LSApplicationQueriesSchemes missing scheme: {scheme}")

# --- localization companion + scaffold docs ---
if not STRINGS.is_file():
    errors.append(f"missing {STRINGS.relative_to(ROOT)} (pt-BR localization companion)")
else:
    stext = STRINGS.read_text(encoding="utf-8")
    for key in privacy_keys:
        if key not in stext:
            errors.append(f"InfoPlist.strings missing {key}")

if not README.is_file():
    errors.append(f"missing {README.relative_to(ROOT)}")

# Store_actions scheme alignment (uber / taxis99 / 99app must exist in Dart)
actions = (ROOT / "frontend/lib/features/results/store_actions.dart").read_text(
    encoding="utf-8"
)
for needle in ("uber://", "taxis99://", "99app://"):
    if needle not in actions:
        errors.append(f"store_actions.dart no longer uses {needle} — update plist schemes")

if errors:
    print("FAIL verify_ios_info_plist:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print(
    "PASS verify_ios_info_plist: privacy keys (#5) + "
    "LSApplicationQueriesSchemes (#10) present and non-empty"
)
sys.exit(0)
