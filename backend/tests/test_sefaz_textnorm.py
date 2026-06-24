"""SEFAZ text normalization shared by mock + HTTP clients (#279)."""

from app.services.sefaz.textnorm import normalize_sefaz_text


def test_normalize_strips_accents_and_casefolds():
    assert normalize_sefaz_text("PÃO de Açúcar") == "pao de acucar"
    assert normalize_sefaz_text("  Feijão   preto ") == "feijao preto"
    assert normalize_sefaz_text("") == ""
    assert normalize_sefaz_text("ARROZ") == "arroz"


def test_normalize_idempotent_for_ascii():
    s = "arroz tipo 1 5kg"
    assert normalize_sefaz_text(s) == s
    assert normalize_sefaz_text(normalize_sefaz_text(s)) == s
