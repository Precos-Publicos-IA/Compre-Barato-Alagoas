"""Phase 4: offline rescore script runs against committed fixture (no network)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
FIXTURE = BACKEND / "tests/fixtures/match_offline_tops.json"
SCRIPT = BACKEND / "scripts/offline_rescore_match.py"
SMOKE = BACKEND / "scripts/match_live_smoke.py"


@pytest.mark.skipif(not FIXTURE.is_file(), reason="fixture missing")
def test_offline_rescore_fixture_schema():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert "results" in data
    assert len(data["results"]) >= 10
    assert any(r.get("live_verdict") == "wrong_class" for r in data["results"])
    assert data.get("poison_pairs")


@pytest.mark.skipif(not SCRIPT.is_file(), reason="script missing")
def test_offline_rescore_script_exits_0(tmp_path: Path):
    out = tmp_path / "rescore.json"
    notes = tmp_path / "rescore.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(FIXTURE),
            "--out",
            str(out),
            "--notes",
            str(notes),
        ],
        cwd=str(REPO),
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(BACKEND)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert out.is_file()
    art = json.loads(out.read_text(encoding="utf-8"))
    s = art["summary"]
    for key in ("n", "still_bad", "now_empty_or_reject", "regressed_good_to_bad"):
        assert key in s, key
    assert s["n"] >= 10
    # 4-S3: poison pairs should all pass with current head spine
    assert s.get("poison_pairs_all_ok") is True
    assert notes.is_file()


@pytest.mark.skipif(not SMOKE.is_file(), reason="smoke script missing")
def test_live_smoke_dry_run_no_network():
    """Live smoke must not hit network in unit CI — dry-run only."""
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--dry-run"],
        cwd=str(REPO),
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(BACKEND)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["concurrency"] == 1
    assert data["n"] >= 12
