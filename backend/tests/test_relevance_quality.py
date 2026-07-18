"""Quality bar for grocery relevance — must keep staples, drop candy/pet noise.

PR1 goldens (phone eval 2026-07-18): reject coco 15 ml under óleo, pasta MAC/OVOS
under ovo, keep soja 900 ml / açúcar 1 kg / egg bandeja class.
"""

from app.services.rag.relevance import (
    score_description,
    filter_offers,
    package_class_rank,
    offer_package_class_ok,
)
from app.services.normalization.matcher import NormalizedOffer


def _o(
    desc: str,
    price: float = 5.0,
    *,
    unit_price: float | None = None,
    quantity: float = 1.0,
    unit: str = "un",
    base_unit: str = "un",
    quantity_parsed: bool = False,
) -> NormalizedOffer:
    return NormalizedOffer(
        description=desc,
        description_sefaz=desc,
        gtin=None,
        unidade_medida="UN",
        price=price,
        unit_price=unit_price if unit_price is not None else price,
        base_unit=base_unit,
        quantity=quantity,
        unit=unit,
        quantity_parsed=quantity_parsed,
        parse_method="description" if quantity_parsed else "fallback",
        parse_confidence=0.9 if quantity_parsed else 0.0,
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


# --- PR1: oil / egg / sugar goldens -------------------------------------------------


def test_oleo_rejects_coco_15ml():
    coco = score_description("oleo", "oleo", "OLEO COCO COPRA 15ML")
    coco_sache = score_description(
        "Óleo", "óleo", "OLEO DE COCO COPRA SACHE 15ML"
    )
    assert coco < 0.2
    assert coco_sache < 0.2


def test_oleo_keeps_soja_900ml():
    soja = score_description("oleo", "oleo", "OLEO SOJA 900ML")
    gir = score_description("oleo", "oleo soja", "OLEO DE GIRASSOL 900ML")
    assert soja > 0.5
    assert gir > 0.5


def test_oleo_filter_drops_coco_keeps_soja():
    offers = [
        _o(
            "OLEO COCO COPRA 15ML",
            price=1.5,
            unit_price=100.0,
            quantity=15.0,
            unit="ml",
            base_unit="L",
            quantity_parsed=True,
        ),
        _o(
            "OLEO SOJA 900ML",
            price=7.0,
            unit_price=7.78,
            quantity=900.0,
            unit="ml",
            base_unit="L",
            quantity_parsed=True,
        ),
    ]
    rel = filter_offers("oleo", "oleo", offers, min_score=0.35)
    descs = [o.description for o in rel.kept]
    assert any("SOJA" in d for d in descs)
    assert not any("COCO" in d for d in descs)


def test_ovo_rejects_mac_ovos_pasta():
    mac = score_description("ovo", "ovo", "MAC OVOS FURADINHO")
    macarr = score_description("ovos", "ovos", "MACARR ESPAGUETE C/OVOS 500G")
    macarrao = score_description("ovo", "ovos", "MACARRAO OVOS FURADINHO 500G")
    assert mac < 0.2
    assert macarr < 0.2
    assert macarrao < 0.2


def test_ovo_keeps_bandeja_and_synonym():
    bandeja = score_description("ovo", "ovo", "OVOS BRANCOS BANDEJA C/12")
    dz = score_description("ovos", "ovos", "OVOS VERMELHO DZ")
    assert bandeja > 0.5
    assert dz > 0.5
    # Singular query must still match plural NFC-e descriptions.
    assert score_description("ovo", "ovo", "OVOS BRANCOS C/20") > 0.45


def test_ovo_demotes_single_vs_dozen():
    single = score_description("ovo", "ovo", "OVO BRANCO UN")
    dozen = score_description("ovo", "ovo", "OVOS BRANCOS BANDEJA C/12")
    assert dozen > single
    # Single may still keep when alone, but package class ranks worse.
    assert package_class_rank("ovo", "ovo", description="OVOS BRANCOS BANDEJA C/12") < (
        package_class_rank("ovo", "ovo", description="OVO BRANCO UN")
    )


def test_acucar_keeps_cristal_1kg():
    sugar = score_description("acucar", "acucar", "ACUCAR CRISTAL 1KG")
    assert sugar > 0.5
    assert package_class_rank(
        "acucar", "acucar", description="ACUCAR CRISTAL 1KG"
    ) == 0


def test_package_class_oil_prefers_cooking_size():
    tiny = package_class_rank("oleo", "oleo", description="OLEO SOJA 15ML")
    cooking = package_class_rank("oleo", "oleo", description="OLEO SOJA 900ML")
    assert cooking < tiny
    assert cooking == 0
    assert tiny >= 3


def test_learn_guard_rejects_coco_oil_class():
    coco = _o(
        "OLEO COCO COPRA 15ML",
        quantity=15.0,
        unit="ml",
        base_unit="L",
        quantity_parsed=True,
    )
    soja = _o(
        "OLEO SOJA 900ML",
        quantity=900.0,
        unit="ml",
        base_unit="L",
        quantity_parsed=True,
    )
    assert not offer_package_class_ok("oleo", "oleo", coco)
    assert offer_package_class_ok("oleo", "oleo", soja)


def test_coco_allowed_when_query_asks_coco():
    # User who typed "óleo de coco" should not hard-lose real coco oil bottles.
    score = score_description("oleo de coco", "oleo de coco", "OLEO DE COCO 200ML")
    assert score > 0.3
