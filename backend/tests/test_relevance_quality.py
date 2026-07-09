"""Quality bar for grocery relevance — must keep staples, drop candy/pet noise."""

from app.services.rag.relevance import score_description, filter_offers
from app.services.normalization.matcher import NormalizedOffer


def _o(desc: str, price: float = 5.0) -> NormalizedOffer:
    return NormalizedOffer(
        description=desc,
        description_sefaz=desc,
        gtin=None,
        unidade_medida="UN",
        price=price,
        unit_price=price,
        base_unit="un",
        quantity=1.0,
        unit="un",
        quantity_parsed=False,
        parse_method="fallback",
        parse_confidence=0.0,
        sale_date=None,
        cnpj="x",
        store_name="S",
        latitude=None,
        longitude=None,
        bairro=None,
        address=None,
    )


def test_leite_prefers_uht_over_candy():
    uht = score_description("leite", "leite uht", "LEITE UHT INTEGRAL ITALAC 1L")
    candy = score_description("leite", "leite", "BALA POCKET LEITE")
    assert uht > 0.45
    assert candy < 0.2
    assert uht > candy


def test_arroz_prefers_tipo1_over_flocao_and_pet():
    rice = score_description("arroz", "arroz tipo 1", "ARROZ TIO JOAO TIPO 1 5KG")
    floc = score_description("arroz", "arroz", "FLOCAO CORINGA ARROZ 200G")
    pet = score_description("arroz", "arroz", "ARROZ P CAES LUPPY 5KG")
    assert rice > 0.5
    assert floc < 0.25
    assert pet < 0.25
    assert rice > floc and rice > pet


def test_feijao_drops_tempero():
    bean = score_description("feijao", "feijao carioca", "FEIJAO CARIOCA TIPO 1 1KG")
    temp = score_description("feijao", "feijao", "TEMPERO PARA FEIJAO 15G")
    assert bean > temp
    assert temp < 0.25


def test_filter_keeps_staples():
    offers = [
        _o("BALA POCKET LEITE", 0.2),
        _o("LEITE UHT BETANIA 1L INTEGRAL", 4.5),
        _o("CARAMELO LEITE CHOCOLATE", 0.3),
    ]
    rel = filter_offers("leite", "leite uht", offers, min_score=0.35)
    assert len(rel.kept) >= 1
    assert all("BALA" not in o.description and "CARAMELO" not in o.description for o in rel.kept)
    assert any("UHT" in o.description for o in rel.kept)
