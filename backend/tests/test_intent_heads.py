"""Systemic head-alignment tests — no per-SKU denylist.

Property: for many carrier HEADs, query=MOD alone must not match ``HEAD de MOD``.
"""

from __future__ import annotations

import pytest

from app.services.rag.intent import (
    alignment_verdict,
    extract_intent,
    heads_compatible,
    rewrite_heads_compatible,
)
from app.services.rag.relevance import score_description
from app.services.rag.store import rewrite_compatible


# --- extract / heads -----------------------------------------------------------


def test_extract_x_de_y():
    i = extract_intent("pão de queijo")
    assert i.head == "pao"
    assert "queijo" in i.modifiers
    assert i.structure == "x_de_y"


def test_extract_single_and_sequence():
    assert extract_intent("queijo").head == "queijo"
    q = extract_intent("queijo mussarela")
    assert q.head == "queijo"
    assert "mussarela" in q.modifiers


def test_heads_compatible_synonyms_and_hypernym():
    assert heads_compatible("ovo", "ovos")
    assert heads_compatible("queijo", "mussarela")
    assert not heads_compatible("queijo", "pao")
    assert not heads_compatible("peito", "pastel")


# --- systemic property: modifier pollution ------------------------------------


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
@pytest.mark.parametrize("mod", ["queijo", "frango", "alho", "camarão", "chocolate"])
def test_property_mod_alone_rejects_carrier_de_mod(carrier: str, mod: str):
    """Query=MOD must not accept HEAD de MOD for arbitrary carriers."""
    desc = f"{carrier.upper()} DE {mod.upper()} 200G"
    # Skip vacuous: if mod is head-compatible with carrier (shouldn't happen)
    if heads_compatible(mod, carrier):
        pytest.skip("carrier/mod synonym")
    assert alignment_verdict(mod, desc) == "reject"
    assert score_description(mod, mod, desc) < 0.2


def test_user_who_asked_for_compound_keeps_it():
    desc = "PAO DE QUEIJO MINI CONGELADO"
    assert alignment_verdict("pão de queijo", desc) == "ok"
    assert score_description("pão de queijo", "pão de queijo", desc) > 0.3


def test_true_product_keeps_head_match():
    assert alignment_verdict("queijo", "QUEIJO MUSSARELA KG") == "ok"
    assert score_description("queijo", "queijo", "QUEIJO MUSSARELA KG") > 0.35
    assert score_description("peito de frango", "peito frango", "PEITO DE FRANGO KG") > 0.3


def test_brand_first_arroz_still_ok():
    # Brand tokens before product head — user head early among content.
    v = alignment_verdict("arroz", "TIO JOAO ARROZ TIPO 1 5KG")
    assert v in ("ok", "unknown")  # must not hard-reject
    assert score_description("arroz", "arroz tipo 1", "TIO JOAO ARROZ TIPO 1 5KG") > 0.45


# --- known incident classes (must die without naming pairs in production) -----


def test_queijo_not_pao_de_queijo():
    assert score_description("queijo", "queijo", "PAO DE QUEIJO") < 0.2
    assert score_description("queijo", "queijo", "PAO DE QUEIJO MINI") < 0.2


def test_frango_not_pastel_or_sopa():
    assert score_description("frango", "frango", "PASTEL DE FRANGO CRE") < 0.2
    assert score_description("frango", "frango", "SOPA VONO PEITO DE FRANGO") < 0.2


def test_peito_de_frango_not_pastel():
    assert (
        score_description("peito de frango", "peito frango", "PASTEL DE FRANGO CRE")
        < 0.2
    )


def test_alho_not_tempero_de_alho():
    assert score_description("alho", "alho", "TEMPERO DE ALHO 50G") < 0.2


# --- rewrites -----------------------------------------------------------------


def test_rewrite_blocks_head_flip_and_modifier_drop():
    assert not rewrite_compatible("queijo", "pao de queijo")
    assert not rewrite_heads_compatible("queijo", "pao de queijo")
    assert not rewrite_compatible("peito de frango", "ovos")
    assert not rewrite_compatible("peito de frango", "frango")  # drops peito head
    assert rewrite_compatible("peito de frango", "peito frango")
    assert rewrite_compatible("queijo", "queijo mussarela")
    assert not rewrite_compatible("papel higiênico", "papel toalha")
    assert rewrite_compatible("pao", "pao frances")


def test_rewrite_blocks_sabao_to_leite():
    assert not rewrite_compatible("sabão em pó", "leite")
