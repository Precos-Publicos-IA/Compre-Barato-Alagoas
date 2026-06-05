"""Quantify normalization quality over the whole mock catalog.

This doubles as the project's tracked metrics: matching accuracy (how many catalog
descriptions yield a usable comparison) and value-comparison quality (how many resolve
to a real per-kg / per-L number rather than the per-package fallback).
"""

import json
from pathlib import Path

from app.services.normalization.matcher import normalize_offer
from tests.conftest import make_registro

_CATALOG = json.loads(
    (Path(__file__).resolve().parent.parent / "app" / "data" / "mock_sefaz.json").read_text(
        encoding="utf-8"
    )
)


def test_catalog_normalization_quality(capsys):
    total = 0
    parsed = 0
    weight_volume = 0
    for p in _CATALOG["products"]:
        reg = make_registro(
            descricao=p["descricao"],
            valor_venda=p["base_price"],
            unidade_medida=p.get("unidadeMedida", "UN"),
            gtin=p.get("gtin") or "",
        )
        offer = normalize_offer(reg)
        assert offer is not None
        total += 1
        if offer.quantity_parsed:
            parsed += 1
        if offer.base_unit in {"kg", "L"}:
            weight_volume += 1

    parse_rate = parsed / total
    value_rate = weight_volume / total
    with capsys.disabled():
        print(
            f"\n[normalization] products={total} "
            f"quantity_parse_rate={parse_rate:.0%} "
            f"weight_or_volume_comparable={value_rate:.0%}"
        )
    # The curated catalog is designed to be highly parseable.
    assert parse_rate >= 0.9
    assert value_rate >= 0.7
