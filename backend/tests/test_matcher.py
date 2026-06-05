from app.services.normalization.matcher import normalize_offer


def test_package_unit_price_from_description(registro_factory):
    reg = registro_factory(descricao="LEITE CAIXA 1L", valor_venda=5.0, unidade_medida="UN")
    offer = normalize_offer(reg)
    assert offer is not None
    assert offer.base_unit == "L"
    assert offer.unit_price == 5.0
    assert offer.parse_method == "description"
    assert offer.quantity_parsed is True


def test_5kg_pack_unit_price(registro_factory):
    reg = registro_factory(descricao="ARROZ TIPO 1 PCT 5KG", valor_venda=24.90, unidade_medida="UN")
    offer = normalize_offer(reg)
    assert offer is not None
    assert offer.base_unit == "kg"
    assert round(offer.unit_price, 2) == 4.98  # 24.90 / 5


def test_loose_by_weight_uses_unidade_medida(registro_factory):
    reg = registro_factory(descricao="BANANA PRATA", valor_venda=4.99, unidade_medida="KG", gtin="")
    offer = normalize_offer(reg)
    assert offer is not None
    assert offer.base_unit == "kg"
    assert offer.unit_price == 4.99
    assert offer.parse_method == "unidade_medida"
    assert offer.quantity_parsed is True


def test_unparsable_falls_back_to_per_unit(registro_factory):
    reg = registro_factory(descricao="PRODUTO GENERICO", valor_venda=3.0, unidade_medida="UN")
    offer = normalize_offer(reg)
    assert offer is not None
    assert offer.base_unit == "un"
    assert offer.unit_price == 3.0
    assert offer.quantity_parsed is False
    assert offer.parse_method == "fallback"


def test_grams_pack_converts_to_kg(registro_factory):
    reg = registro_factory(descricao="CAFE 250G", valor_venda=9.90, unidade_medida="UN")
    offer = normalize_offer(reg)
    assert offer is not None
    assert offer.base_unit == "kg"
    assert round(offer.unit_price, 2) == 39.60  # 9.90 / 0.25


def test_no_sale_returns_none(registro_factory):
    reg = registro_factory(descricao="LEITE 1L", valor_venda=5.0)
    reg.produto.venda = None
    assert normalize_offer(reg) is None
