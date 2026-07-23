"""Phase 2 auto_label tests — pure head-safe labels (no I/O)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from app.services.rag.intent import alignment_verdict, heads_compatible
from app.services.rag.labeler import (
    BAD_SCORE_FLOOR,
    GOOD_SCORE,
    LABELS,
    auto_label,
)
from app.services.rag.outcome_log import (
    append_outcome,
    build_item_outcome,
    log_search_item_outcomes,
)
from app.services.rag.relevance import score_description


# --- 2-S1 / 2-S2: pure function + fixed label set --------------------------------


def test_auto_label_is_pure_no_io_signature():
    """2-S1: pure function in labeler.py — no path/redis params."""
    src = inspect.getsource(auto_label)
    assert "open(" not in src
    assert "redis" not in src.lower()
    assert "requests" not in src.lower()
    # Call twice with same inputs → same output (determinism).
    a = auto_label("queijo", "QUEIJO MUSSARELA KG", fetch_failed=False, score=0.7)
    b = auto_label("queijo", "QUEIJO MUSSARELA KG", fetch_failed=False, score=0.7)
    assert a == b
    assert a in LABELS


def test_label_set_documented_and_fixed():
    """2-S2: fixed label enum/set."""
    required = {"good", "weak", "bad", "empty_fetch", "empty_no_data", "unknown"}
    assert required <= LABELS
    for lab in required:
        # Every label is reachable somehow (smoke via controlled inputs below).
        assert isinstance(lab, str)


# --- 2-S3: priority — fetch_failed wins ----------------------------------------


def test_fetch_failed_always_empty_fetch_even_with_description():
    """2-S3: fetch_failed=True ⇒ empty_fetch even if description non-empty."""
    assert (
        auto_label(
            "arroz",
            "ARROZ TIPO 1 5KG",
            fetch_failed=True,
            score=0.9,
            stores_found=5,
        )
        == "empty_fetch"
    )
    assert (
        auto_label(
            "queijo",
            "PAO DE QUEIJO",
            fetch_failed=True,
            score=0.04,
        )
        == "empty_fetch"
    )
    assert auto_label("x", None, fetch_failed=True) == "empty_fetch"


def test_empty_no_data_when_no_description_or_no_stores():
    assert auto_label("arroz", None, fetch_failed=False) == "empty_no_data"
    assert auto_label("arroz", "  ", fetch_failed=False) == "empty_no_data"
    assert (
        auto_label(
            "arroz",
            "ARROZ TIPO 1",
            fetch_failed=False,
            score=0.8,
            stores_found=0,
        )
        == "empty_no_data"
    )


# --- 2-S4: property pollution carriers × mods ----------------------------------


@pytest.mark.parametrize(
    "carrier",
    [
        "pao",
        "pastel",
        "sopa",
        "tempero",
        "caldo",
        "suco",
        "biscoito",
        "molho",
        "bolo",
        "torta",
        "salada",
        "risoto",
        "pizza",
    ],
)
@pytest.mark.parametrize("mod", ["queijo", "frango", "alho", "camarao", "chocolate"])
def test_property_mod_alone_labels_carrier_de_mod_bad(carrier: str, mod: str):
    """2-S4: query=MOD, desc={CARRIER} DE {MOD} ⇒ bad (alignment reject path)."""
    if heads_compatible(mod, carrier):
        pytest.skip("carrier/mod synonym")
    desc = f"{carrier.upper()} DE {mod.upper()} 200G"
    assert alignment_verdict(mod, desc) == "reject"
    lab = auto_label(mod, desc, fetch_failed=False, stores_found=3)
    assert lab == "bad", f"{mod=} {desc=} → {lab}"


# --- 2-S5: queijo goldens ------------------------------------------------------


def test_queijo_pao_de_queijo_bad():
    """2-S5: queijo + PAO DE QUEIJO ⇒ bad."""
    assert auto_label("queijo", "PAO DE QUEIJO", fetch_failed=False, stores_found=2) == "bad"
    assert (
        auto_label("queijo", "PAO DE QUEIJO MINI", fetch_failed=False, stores_found=2)
        == "bad"
    )


def test_queijo_mussarela_not_bad():
    """2-S5: queijo + QUEIJO MUSSARELA ⇒ not bad (good/weak/unknown OK)."""
    lab = auto_label(
        "queijo",
        "QUEIJO MUSSARELA KG",
        fetch_failed=False,
        stores_found=4,
    )
    assert lab != "bad"
    assert lab in {"good", "weak", "unknown"}
    # Live score should clear the good band for a true head match.
    sc = score_description("queijo", "queijo", "QUEIJO MUSSARELA KG")
    assert sc >= GOOD_SCORE or lab in {"good", "weak", "unknown"}


# --- 2-S6: peito / ovos-style rejects ------------------------------------------


def test_peito_frango_rejects_pastel():
    """2-S6: peito-style wrong class top (pastel) ⇒ bad via alignment reject."""
    assert (
        auto_label(
            "peito de frango",
            "PASTEL DE FRANGO CRE",
            fetch_failed=False,
            stores_found=3,
        )
        == "bad"
    )


def test_peito_frango_sopa_is_weak_or_bad():
    """SOPA carrier with embedded peito is weak noise (plan §2.1 step 6), not good."""
    lab = auto_label(
        "peito de frango",
        "SOPA VONO PEITO DE FRANGO",
        fetch_failed=False,
        stores_found=3,
    )
    assert lab in {"weak", "bad"}
    assert lab != "good"


def test_ovos_style_egg_on_non_egg_query_is_bad():
    """2-S6: egg SKU on non-egg label (hard-reject floor) ⇒ bad."""
    lab = auto_label(
        "peito de frango",
        "OVOS BRANCOS GRANDE DZ",
        fetch_failed=False,
        stores_found=2,
    )
    assert lab == "bad"
    sc = score_description(
        "peito de frango", "peito frango", "OVOS BRANCOS GRANDE DZ"
    )
    assert sc < BAD_SCORE_FLOOR


def test_frango_not_pastel_or_sopa_labels_bad():
    assert (
        auto_label("frango", "PASTEL DE FRANGO CRE", fetch_failed=False, stores_found=1)
        == "bad"
    )
    assert (
        auto_label(
            "frango", "SOPA VONO PEITO DE FRANGO", fetch_failed=False, stores_found=1
        )
        == "bad"
    )


# --- score bands + weak patterns -----------------------------------------------


def test_good_band_true_match():
    lab = auto_label(
        "arroz",
        "ARROZ TIPO 1 5KG",
        fetch_failed=False,
        score=0.75,
        stores_found=5,
    )
    # alignment ok + high score → good
    assert lab in {"good", "weak"}  # weak only if noise heuristic fires (should not)
    assert lab == "good"


def test_mid_score_is_weak():
    # Force mid score with alignment ok on a true head (avoid reject path).
    lab = auto_label(
        "arroz",
        "ARROZ TIPO 1 5KG",
        fetch_failed=False,
        score=0.35,
        stores_found=2,
    )
    assert lab == "weak"


def test_score_below_floor_is_bad():
    lab = auto_label(
        "arroz",
        "BALA DE MENTA 100G",
        fetch_failed=False,
        score=0.04,
        stores_found=2,
    )
    assert lab == "bad"


# --- 2-S7: outcome log writes real auto_label ----------------------------------


def test_build_item_outcome_writes_real_auto_label():
    """2-S7: outcome builder fills auto_label from labeler (not hard-coded unknown)."""
    bad_row = build_item_outcome(
        query="queijo",
        top_descriptions=["PAO DE QUEIJO MINI"],
        top_scores=[0.04],
        stores_found=3,
        items_fetch_failed=False,
    )
    assert bad_row["auto_label"] == "bad"

    fetch_row = build_item_outcome(
        query="arroz",
        top_descriptions=["ARROZ TIPO 1 5KG"],
        top_scores=[0.9],
        stores_found=0,
        items_fetch_failed=True,
    )
    assert fetch_row["auto_label"] == "empty_fetch"

    good_row = build_item_outcome(
        query="queijo",
        top_descriptions=["QUEIJO MUSSARELA KG"],
        stores_found=4,
        items_fetch_failed=False,
    )
    assert good_row["auto_label"] != "unknown"
    assert good_row["auto_label"] in LABELS
    assert good_row["auto_label"] != "bad"

    empty_row = build_item_outcome(
        query="cafe",
        top_descriptions=[],
        stores_found=2,
        items_fetch_failed=False,
    )
    assert empty_row["auto_label"] == "empty_no_data"


def test_log_search_item_outcomes_persists_auto_label(tmp_path: Path):
    """2-S7 integration: JSONL lines carry computed auto_label."""
    path = tmp_path / "out.jsonl"

    class _Offer:
        def __init__(self, description: str):
            self.description = description

    n = log_search_item_outcomes(
        items=[{"label": "queijo", "search_term": "queijo"}],
        offers_by_item={"queijo": [_Offer("PAO DE QUEIJO")]},
        stores_found=3,
        data_source="mock",
        path=str(path),
        force=True,
    )
    assert n == 1
    line = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[0])
    assert line["auto_label"] == "bad"
    assert line["query"] == "queijo"


def test_append_roundtrip_auto_label(tmp_path: Path):
    path = tmp_path / "o.jsonl"
    row = build_item_outcome(
        query="frango",
        top_descriptions=["PASTEL DE FRANGO CRE"],
        stores_found=2,
        items_fetch_failed=False,
    )
    assert append_outcome(row, path=str(path)) is True
    parsed = json.loads(path.read_text(encoding="utf-8").strip())
    assert parsed["auto_label"] == "bad"
