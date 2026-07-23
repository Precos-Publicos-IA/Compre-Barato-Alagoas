"""Phase 5 lexicon mining + optional load (5-S1…5-S5, 5-S7)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from app.services.rag import lexicon as lex_mod
from app.services.rag.intent import (
    expand_synonyms,
    heads_compatible,
)
from app.services.rag.lexicon import (
    ENV_MATCH_LEXICON_PATH,
    clear_match_lexicon,
    is_lexicon_loaded,
    lexicon_known_heads,
    lexicon_promoted_syn_groups,
    load_match_lexicon,
)

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
SCRIPT = BACKEND / "scripts" / "mine_match_lexicon.py"
FIXTURE = BACKEND / "tests" / "fixtures" / "match_lexicon_mine_sample.jsonl"

# Import miner helpers
sys.path.insert(0, str(BACKEND / "scripts"))
# Load module by path to avoid package name issues
import importlib.util

_spec = importlib.util.spec_from_file_location("mine_match_lexicon", SCRIPT)
assert _spec and _spec.loader
mine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mine)


@pytest.fixture(autouse=True)
def _reset_lexicon(monkeypatch):
    clear_match_lexicon()
    monkeypatch.delenv(ENV_MATCH_LEXICON_PATH, raising=False)
    yield
    clear_match_lexicon()
    monkeypatch.delenv(ENV_MATCH_LEXICON_PATH, raising=False)


# --- 5-S3: filter never emits cross-head poison --------------------------------


def test_s3_filter_drops_queijo_pao():
    raw = [
        ("queijo", "pao"),
        ("queijo", "pao"),
        {"a": "frango", "b": "pastel", "co_success": 99},
        ("ovo", "ovos"),
        {"a": "queijo", "b": "mussarela", "co_success": 5},
        ("peito", "pastel"),
    ]
    kept = mine.filter_synonym_pairs(raw)
    pairs = {(r["a"], r["b"]) for r in kept}
    # normalized sorted keys inside filter
    flat = set()
    for a, b in pairs:
        flat.add(tuple(sorted((a, b))))
    assert ("pao", "queijo") not in flat
    assert ("frango", "pastel") not in flat
    assert ("pastel", "peito") not in flat
    assert ("ovo", "ovos") in flat
    # mussarela is hypernym-compatible with queijo
    assert any(heads_compatible(r["a"], r["b"]) for r in kept)
    for r in kept:
        assert r["heads_compatible"] is True
        assert heads_compatible(r["a"], r["b"])


def test_s3_filter_property_no_incompatible():
    poison = [
        ("queijo", "pao"),
        ("frango", "pastel"),
        ("ovo", "macarrao"),
        ("alho", "tempero"),
        ("chocolate", "bolo"),
        ("maca", "macarrao"),  # prefix false friend
    ]
    # mix with one good
    poison.append(("feijao", "feijoes"))
    kept = mine.filter_synonym_pairs(poison)
    for r in kept:
        assert heads_compatible(r["a"], r["b"]), r
        assert mine.synonym_pair_safe(r["a"], r["b"])
    flat = {tuple(sorted((r["a"], r["b"]))) for r in kept}
    assert ("maca", "macarrao") not in flat
    assert ("feijao", "feijoes") in flat


# --- 5-S1 / 5-S2 / 5-S7: dry-run fixture < 60s, versioned schema, staples -----


def test_s1_s2_s7_dry_run_fixture(tmp_path):
    assert FIXTURE.is_file()
    out = tmp_path / "heads_lexicon.dry.json"
    t0 = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(FIXTURE),
            "--out",
            str(out),
            "--dry-run",
            "--min-head-count",
            "1",
        ],
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(BACKEND)},
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - t0
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert elapsed < 60.0, f"dry-run took {elapsed:.1f}s"
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    # schema
    assert data.get("schema_version") == 1
    assert data.get("version")
    assert data.get("generated_at")
    assert "source" in data
    assert isinstance(data.get("heads"), list)
    assert isinstance(data.get("synonym_candidates"), list)
    assert data.get("promoted_synonym_groups") == []
    tokens = {h["token"] for h in data["heads"] if isinstance(h, dict)}
    # staples present on fixture (5-S7)
    for staple in ("arroz", "feijao", "leite"):
        assert staple in tokens, f"missing staple {staple} in {sorted(tokens)}"
    # no cross-head synonym candidates
    for s in data["synonym_candidates"]:
        assert heads_compatible(s["a"], s["b"])
        assert not (
            {s["a"], s["b"]} == {"queijo", "pao"}
            or {s["a"], s["b"]} == {"frango", "pastel"}
        )


def test_mine_records_skips_fetch_failed():
    rows = [
        {
            "request": {"items": ["arroz"]},
            "summary": {
                "stores_found": 0,
                "items_fetch_failed": 1,
                "top_description": None,
            },
            "response": {"stores": []},
        },
        {
            "request": {"items": ["arroz"]},
            "summary": {
                "stores_found": 2,
                "items_fetch_failed": 0,
                "top_description": "ARROZ TIPO 1 5KG",
            },
            "response": {
                "stores": [
                    {
                        "items": [
                            {
                                "query": "arroz",
                                "found": True,
                                "description": "ARROZ TIPO 1 5KG",
                            }
                        ]
                    }
                ]
            },
        },
    ]
    art = mine.mine_records(rows, min_head_count=1, min_co_success=1)
    assert art["meta"]["n_skipped_fetch"] >= 1
    assert art["meta"]["n_usable"] >= 1
    tokens = {h["token"] for h in art["heads"]}
    assert "arroz" in tokens
    assert art["promoted_synonym_groups"] == []


def test_mine_never_emits_poison_synonym_from_bad_top():
    """Even if a wrong-class top is stored with stores>0, heads must not pair."""
    rows = [
        {
            "request": {"items": ["queijo"]},
            "summary": {
                "stores_found": 2,
                "items_fetch_failed": 0,
                "top_description": "PAO DE QUEIJO CONGELADO 1KG",
            },
            "response": {
                "stores": [
                    {
                        "items": [
                            {
                                "query": "queijo",
                                "found": True,
                                "description": "PAO DE QUEIJO CONGELADO 1KG",
                            }
                        ]
                    }
                ]
            },
        }
    ]
    art = mine.mine_records(rows, min_head_count=1)
    for s in art["synonym_candidates"]:
        assert {s["a"], s["b"]} != {"pao", "queijo"}
        assert heads_compatible(s["a"], s["b"])


# --- 5-S4 / 5-S5: load opt-in; default unchanged; with load goldens-safe ------


def test_s4_default_no_lexicon():
    assert not is_lexicon_loaded()
    # expand_synonyms still works with hard-coded groups
    assert "ovos" in expand_synonyms({"ovo"})
    assert not lex_mod.lexicon_env_path()


def test_s4_load_via_path_and_env(tmp_path, monkeypatch):
    lex_path = tmp_path / "heads_lexicon.v1.json"
    lex_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "v1",
                "generated_at": "2026-07-23T00:00:00Z",
                "source": {"paths": ["fixture"], "kind": "test"},
                "heads": [
                    {"token": "arroz", "count": 10},
                    {"token": "feijao", "count": 8},
                    {"token": "leite", "count": 7},
                ],
                "synonym_candidates": [
                    {"a": "ovo", "b": "ovos", "co_success": 3, "heads_compatible": True}
                ],
                # candidates must NOT be applied:
                "promoted_synonym_groups": [],
            }
        ),
        encoding="utf-8",
    )
    data = load_match_lexicon(lex_path)
    assert is_lexicon_loaded()
    assert "arroz" in lexicon_known_heads()
    assert lexicon_promoted_syn_groups() == ()
    # raw candidates present but not applied
    assert data["synonym_candidates"]
    # invent a fake pair that is only in candidates — should NOT expand
    # (ovo/ovos is hard-coded already; use a fake promoted-only check below)

    clear_match_lexicon()
    monkeypatch.setenv(ENV_MATCH_LEXICON_PATH, str(lex_path))
    # expand_synonyms triggers maybe_autoload
    _ = expand_synonyms({"arroz"})
    assert is_lexicon_loaded()
    assert "arroz" in lexicon_known_heads()


def test_s4_promoted_groups_apply_only_when_reviewed(tmp_path):
    """promoted_synonym_groups expand; synonym_candidates do not."""
    lex_path = tmp_path / "lex.json"
    # Use a pair NOT in hard-coded _SYN_GROUPS
    lex_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "v1",
                "generated_at": "2026-07-23T00:00:00Z",
                "source": {},
                "heads": [{"token": "iogurte", "count": 1}],
                "synonym_candidates": [
                    {
                        "a": "iogurte",
                        "b": "yogurt",
                        "co_success": 9,
                        "heads_compatible": True,
                    }
                ],
                "promoted_synonym_groups": [],
            }
        ),
        encoding="utf-8",
    )
    load_match_lexicon(lex_path)
    assert "yogurt" not in expand_synonyms({"iogurte"})

    clear_match_lexicon()
    lex_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "v1",
                "generated_at": "2026-07-23T00:00:00Z",
                "source": {},
                "heads": [{"token": "iogurte", "count": 1}],
                "synonym_candidates": [],
                "promoted_synonym_groups": [["iogurte", "yogurt"]],
            }
        ),
        encoding="utf-8",
    )
    load_match_lexicon(lex_path)
    assert "yogurt" in expand_synonyms({"iogurte"})
    assert heads_compatible("iogurte", "yogurt")


def test_s5_with_lexicon_loaded_core_properties_hold(tmp_path):
    """Loading miner-style lexicon must not break head pollution property."""
    # Mine fixture → load → check reject still holds
    art = mine.mine_paths([FIXTURE], min_head_count=1)
    path = tmp_path / "from_fixture.json"
    path.write_text(json.dumps(art), encoding="utf-8")
    load_match_lexicon(path)
    assert is_lexicon_loaded()

    from app.services.rag.intent import alignment_verdict
    from app.services.rag.relevance import score_description

    for carrier in ("pao", "pastel", "sopa"):
        desc = f"{carrier.upper()} DE QUEIJO 200G"
        assert alignment_verdict("queijo", desc) == "reject"
        assert score_description("queijo", "queijo", desc) < 0.2
    assert not heads_compatible("queijo", "pao")


def test_usable_row_helper():
    assert mine.is_usable_match_row(
        stores_found=1, items_fetch_failed=False, description="ARROZ 1KG"
    )
    assert not mine.is_usable_match_row(
        stores_found=0, items_fetch_failed=False, description="ARROZ 1KG"
    )
    assert not mine.is_usable_match_row(
        stores_found=3, items_fetch_failed=True, description="ARROZ 1KG"
    )
    assert not mine.is_usable_match_row(
        stores_found=3, items_fetch_failed=False, description=""
    )
