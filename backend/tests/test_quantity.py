"""Quantity extraction is the key accuracy metric — exercise it hard."""

import pytest

from app.services.normalization.quantity import extract_quantity


@pytest.mark.parametrize(
    "desc,base_value,base_unit,multipack",
    [
        ("LEITE NA CAIXA INTEGRAL 1L", 1.0, "L", False),
        ("ARROZ BRANCO TIPO 1 PCT 5KG", 5.0, "kg", False),
        ("ARROZ TIPO1 NAMORADO 1KG", 1.0, "kg", False),
        ("CAFE TORRADO E MOIDO A VACUO 250G", 0.25, "kg", False),
        ("OLEO DE SOJA 900ML", 0.9, "L", False),
        ("REFRIGERANTE 1,5 L", 1.5, "L", False),
        ("MACARRAO ESPAGUETE SEMOLA 500G", 0.5, "kg", False),
        ("SABAO EM PO CAIXA 800G", 0.8, "kg", False),
        ("CERVEJA PILSEN LATA 350ML C/12", 4.2, "L", True),
        ("AGUA MINERAL 12X500ML", 6.0, "L", True),
        ("OVOS BRANCOS GRANDES C/12", 12.0, "un", True),
    ],
)
def test_extract_known_sizes(desc, base_value, base_unit, multipack):
    pq = extract_quantity(desc)
    assert pq is not None, desc
    assert pq.base_unit == base_unit
    assert pq.base_value == pytest.approx(base_value, rel=1e-6)
    assert pq.multipack is multipack


def test_mg_dosage_ignored_uses_pack_count():
    # Medicine strength in mg must not be read as a package size; the C/10 wins.
    pq = extract_quantity("DIPIRONA SODICA 500MG COMPRIMIDO C/10")
    assert pq is not None
    assert pq.base_unit == "un"
    assert pq.base_value == 10.0


def test_no_size_returns_none():
    assert extract_quantity("BANANA PRATA") is None
    assert extract_quantity("TOMATE") is None
    assert extract_quantity("") is None


def test_does_not_match_unit_inside_word():
    # "TIPO1" must not be read as a size; no trailing unit present.
    assert extract_quantity("ARROZ TIPO1 NACIONAL") is None


def test_decimal_comma_and_dot_equivalent():
    a = extract_quantity("REFRI 2,5L")
    b = extract_quantity("REFRI 2.5L")
    assert a and b and a.base_value == pytest.approx(b.base_value)


def test_explicit_single_count_unit_is_parsed():
    """Probe: '1UN', '1 pc', '1 unidade' must parse as quantity (not fallback).
    Previously the >1 guard dropped legitimate single count markers."""
    for desc in ("ITEM 1UN", "WIDGET 1 PC", "COISA 1 UNIDADE"):
        pq = extract_quantity(desc)
        assert pq is not None, desc
        assert pq.base_unit == "un"
        assert pq.base_value == pytest.approx(1.0)
