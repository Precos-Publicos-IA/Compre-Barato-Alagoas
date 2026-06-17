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


def test_requested_quantity_scales_totals(registro_factory):
    # User wants 3x arroz (8.0 each) + 1x leite (6.0). Total = 3*8 + 6 = 30.
    a = _offer(registro_factory(descricao="ARROZ 1KG", valor_venda=8.0, cnpj="A", nome="A"))
    leite = _offer(registro_factory(descricao="LEITE 1L", valor_venda=6.0, cnpj="A", nome="A"))
    results = build_store_results(
        ["arroz", "leite"],
        {"arroz": [a], "leite": [leite]},
        origin=None,
        top_n=5,
        quantities={"arroz": 3, "leite": 1},
    )
    store = results[0]
    assert store.total == 30.0
    arroz_line = next(i for i in store.items if i.query == "arroz")
    assert arroz_line.requested_quantity == 3
    assert arroz_line.line_total == 24.0
    assert arroz_line.price == 8.0  # per-package price unchanged


def test_quantity_defaults_to_one(registro_factory):
    a = _offer(registro_factory(descricao="ARROZ 1KG", valor_venda=8.0, cnpj="A"))
    results = build_store_results(["arroz"], {"arroz": [a]}, origin=None, top_n=5)
    item = results[0].items[0]
    assert item.requested_quantity == 1
    assert item.line_total == 8.0


def test_excluded_cnpjs_filtered_before_top_n(registro_factory):
    # Two stores stock the item; B is cheaper, so B wins the single slot by default.
    a = _offer(registro_factory(descricao="ARROZ 1KG", valor_venda=9.0, cnpj="A", nome="A"))
    b = _offer(registro_factory(descricao="ARROZ 1KG", valor_venda=5.0, cnpj="B", nome="B"))
    top1 = build_store_results(["arroz"], {"arroz": [a, b]}, origin=None, top_n=1)
    assert top1[0].cnpj == "B"
    # Hiding B must free its slot for A — i.e. filtered BEFORE ranking/truncation,
    # not dropped after (which would leave an empty result).
    excl = build_store_results(
        ["arroz"], {"arroz": [a, b]}, origin=None, top_n=1, excluded_cnpjs={"B"}
    )
    assert [s.cnpj for s in excl] == ["A"]
