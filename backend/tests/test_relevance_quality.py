"""Quality bar for grocery relevance — must keep staples, drop candy/pet noise.

PR1 goldens (phone eval 2026-07-18): reject coco 15 ml under óleo, pasta MAC/OVOS
under ovo, keep soja 900 ml / açúcar 1 kg / egg bandeja class.

PR2 goldens (match_eval_100 live 2026-07-18): egg cross-bleed, sal snacks,
óleo saturado, feijão tempero, zero-açúcar candy, café caramel/spice mix.
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


# --- PR2 / match_eval_100 P0 goldens ---------------------------------------------


def test_egg_cross_bleed_rejected_for_non_egg_queries():
    """Unrelated intents must never keep OVOS BRANCOS UND (live bleed theme T1)."""
    egg_descs = [
        "OVOS BRANCOS UND",
        "OVOS EXTRA STA MARIA LUNA UN",
        "OVOS BRANCO - UNIDADE",
        "OVOS",
    ]
    non_egg_queries = [
        "farinha de trigo",
        "queijo",
        "pão",
        "água",
        "molho de tomate",
        "peito de frango",
        "saco de lixo",
        "barra de cereal",
        "água sanitária",
    ]
    for q in non_egg_queries:
        for d in egg_descs:
            s = score_description(q, q, d)
            assert s < 0.15, f"{q!r} vs {d!r} scored {s}"


def test_egg_still_matches_egg_intent():
    assert score_description("ovo", "ovo", "OVOS BRANCOS UND") > 0.25
    assert score_description("ovos", "ovos", "OVOS EXTRA STA MARIA LUNA UN") > 0.25


def test_sal_rejects_snacks_keeps_refinado():
    castanha = score_description("sal", "sal", "CASTANHA CAJU CROC TORRADA S SAL 50G")
    pipoca = score_description("sal", "sal", "PIPOCA BETTI 15G SAL")
    salg = score_description("sal", "sal", "SALG MILHO CORINGUITOS CEB SAL 30G")
    refinado = score_description("sal", "sal", "SAL REFINADO CISNE 1KG")
    assert castanha < 0.2
    assert pipoca < 0.2
    assert salg < 0.2
    assert refinado > 0.5
    assert refinado > castanha


def test_sal_filter_drops_snacks():
    offers = [
        _o("CASTANHA CAJU CROC TORRADA S SAL 50G", price=0.33, unit_price=6.6),
        _o("PIPOCA BETTI 15G SAL", price=0.5),
        _o("SAL REFINADO CISNE 1KG", price=2.5, unit_price=2.5, quantity=1.0, unit="kg", base_unit="kg", quantity_parsed=True),
    ]
    rel = filter_offers("sal", "sal", offers, min_score=0.35)
    descs = [o.description for o in rel.kept]
    assert any("REFINADO" in d for d in descs)
    assert not any("CASTANHA" in d or "PIPOCA" in d for d in descs)


def test_oleo_rejects_saturado_and_fish_oil():
    sat = score_description("oleo", "oleo", "OLEO SATURADO 1LT")
    mist = score_description("oleo", "oleo", "MIST.LEITE E OLEO V.DAMARE 17% 200G")
    sard = score_description("oleo", "oleo", "SARD.PALMEIRA OLEO")
    soja = score_description("oleo", "oleo", "OLEO DE SOJA SOYA 900ML")
    assert sat < 0.2
    assert mist < 0.2
    assert sard < 0.2
    assert soja > 0.5
    assert soja > sat


def test_oleo_de_soja_filter_prefers_cooking():
    offers = [
        _o("OLEO SATURADO 1LT", price=2.0, unit_price=2.0, quantity=1.0, unit="L", base_unit="L", quantity_parsed=True),
        _o("MIST.LEITE E OLEO V.DAMARE 17% 200G", price=3.0),
        _o(
            "OLEO DE SOJA SOYA 900ML",
            price=7.0,
            unit_price=7.78,
            quantity=900.0,
            unit="ml",
            base_unit="L",
            quantity_parsed=True,
        ),
        _o("SARD.PALMEIRA OLEO", price=4.0),
    ]
    rel = filter_offers("óleo de soja", "óleo de soja", offers, min_score=0.35)
    descs = [o.description for o in rel.kept]
    assert any("SOJA" in d for d in descs)
    assert not any("SATURADO" in d for d in descs)
    assert not any("SARD" in d for d in descs)


def test_feijao_rejects_tempero_abbrev_and_typos():
    # Live SEFAZ lines use TEMPE. / TEMPEIRO, not only TEMPERO.
    bean = score_description("feijão", "feijão", "FEIJAO PT T1 1KG OF3")
    tempe = score_description("feijão", "feijão", "TEMPE.PARA FEIJAO BOM PALADAR 15g")
    tempeiro = score_description("feijão", "feijão", "TEMPEIRO PARA FEIJAO 10G")
    tempero = score_description("feijao", "feijao", "TEMPERO PARA FEIJAO 15G")
    assert bean > 0.5
    assert tempe < 0.2
    assert tempeiro < 0.2
    assert tempero < 0.2
    assert bean > tempe


def test_feijao_preto_filter_keeps_beans():
    offers = [
        _o("TEMPE.PARA FEIJAO BOM PALADAR 15g", price=1.5, unit_price=100.0),
        _o("TEMPEIRO PARA FEIJAO 10G", price=1.79, unit_price=179.0),
        _o(
            "FEIJAO PT T1 1KG OF3",
            price=2.25,
            unit_price=2.25,
            quantity=1.0,
            unit="kg",
            base_unit="kg",
            quantity_parsed=True,
        ),
    ]
    rel = filter_offers("feijão preto", "feijão preto", offers, min_score=0.35)
    descs = [o.description for o in rel.kept]
    assert any("FEIJAO PT" in d or "FEIJAO" in d and "TEMP" not in d for d in descs)
    assert not any("TEMP" in d for d in descs)


def test_acucar_rejects_zero_sugar_candy():
    candy = score_description("açúcar", "açúcar", "BIGBIG ZERO ACUCAR C 4")
    sachet = score_description("açúcar", "açúcar", "ACUCAR 40G AZUL (SCH) FACA A FESTA")
    cristal = score_description("açúcar", "açúcar", "ACUCAR CRISTAL ESPECIAL FORMOSO 1KG")
    assert candy < 0.2
    assert sachet < 0.25
    assert cristal > 0.5
    assert cristal > candy


def test_acucar_filter_drops_candy():
    offers = [
        _o("BIGBIG ZERO ACUCAR C 4", price=0.5),
        _o("ACUCAR 40G AZUL (SCH) FACA A FESTA", price=0.4),
        _o(
            "ACUCAR CRISTAL ESPECIAL FORMOSO 1KG",
            price=4.0,
            unit_price=4.0,
            quantity=1.0,
            unit="kg",
            base_unit="kg",
            quantity_parsed=True,
        ),
    ]
    rel = filter_offers("açúcar", "açúcar", offers, min_score=0.35)
    descs = [o.description for o in rel.kept]
    assert any("CRISTAL" in d for d in descs)
    assert not any("BIGBIG" in d or "ZERO" in d for d in descs)


def test_cafe_rejects_caramel_and_spice_mix():
    spice = score_description("café", "café", "Coracao, Cafe, Canela")
    caramel = score_description("café", "café", "CARAMELOS CAFE COM LEITE 1 UN")
    real = score_description("café", "café", "CAFE TORRADO MOIDO 500G")
    assert spice < 0.2
    assert caramel < 0.2
    assert real > 0.5
    assert real > spice


def test_cafe_soluvel_keeps_product():
    s = score_description("café solúvel", "café solúvel", "CAFE SOLUVEL NESCAFE 100G")
    assert s > 0.45


def test_filter_non_egg_query_drops_eggs_entirely():
    offers = [
        _o("OVOS BRANCOS UND", price=0.5),
        _o("OVOS EXTRA STA MARIA LUNA UN", price=0.6),
        _o("FARINHA DE TRIGO 1KG", price=5.0, unit_price=5.0, quantity=1.0, unit="kg", base_unit="kg", quantity_parsed=True),
    ]
    rel = filter_offers("farinha de trigo", "farinha de trigo", offers, min_score=0.35)
    assert all("OVOS" not in o.description for o in rel.kept)
    assert any("FARINHA" in o.description for o in rel.kept)
