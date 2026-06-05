from app.services.normalization.matcher import normalize_offer
from app.services.ranking import build_store_results


def _offer(reg):
    o = normalize_offer(reg)
    assert o is not None
    return o


def test_best_value_offer_chosen_per_store(registro_factory):
    # Same store has 1kg @ 7.0 (7/kg) and 5kg @ 25.0 (5/kg) -> 5kg is better value.
    a = _offer(registro_factory(descricao="ARROZ 1KG", valor_venda=7.0, cnpj="A"))
    b = _offer(registro_factory(descricao="ARROZ 5KG", valor_venda=25.0, cnpj="A"))
    results = build_store_results(["arroz"], {"arroz": [a, b]}, origin=None, top_n=5)
    assert len(results) == 1
    item = results[0].items[0]
    assert item.unit_price == 5.0
    assert item.price == 25.0


def test_ranking_prefers_more_items_then_cheaper(registro_factory):
    # Store A has both items; store B has only one (cheaper) item.
    a1 = _offer(registro_factory(descricao="ARROZ 1KG", valor_venda=8.0, cnpj="A", nome="A"))
    a2 = _offer(registro_factory(descricao="LEITE 1L", valor_venda=6.0, cnpj="A", nome="A"))
    b1 = _offer(registro_factory(descricao="ARROZ 1KG", valor_venda=5.0, cnpj="B", nome="B"))
    results = build_store_results(
        ["arroz", "leite"],
        {"arroz": [a1, b1], "leite": [a2]},
        origin=None,
        top_n=5,
    )
    assert results[0].cnpj == "A"  # has 2/2 items, beats cheaper-but-partial B
    assert results[0].items_found == 2
    assert results[1].cnpj == "B"
    assert results[1].missing == ["leite"]


def test_distance_computed_when_origin_given(registro_factory):
    a = _offer(registro_factory(descricao="ARROZ 1KG", valor_venda=8.0, lat=-9.66, lon=-35.70))
    results = build_store_results(["arroz"], {"arroz": [a]}, origin=(-9.65, -35.71), top_n=5)
    assert results[0].distance_km is not None
    assert results[0].distance_km < 5
