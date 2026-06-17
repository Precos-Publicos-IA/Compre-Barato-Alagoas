import pytest

from app.services.llm.mock_client import MockLLMClient


@pytest.mark.asyncio
async def test_splits_compound_line():
    llm = MockLLMClient()
    items = (await llm.parse_list(["arroz, feijão e leite"])).items
    terms = {i.search_term.lower() for i in items}
    assert {"arroz", "feijão", "leite"} <= terms


@pytest.mark.asyncio
async def test_strips_size_and_count():
    llm = MockLLMClient()
    items = (await llm.parse_list(["2 arroz 5kg"])).items
    assert len(items) == 1
    assert items[0].search_term.lower() == "arroz"
    assert items[0].quantity == 2


@pytest.mark.asyncio
async def test_dedupes():
    llm = MockLLMClient()
    items = (await llm.parse_list(["leite", "leite"])).items
    assert len(items) == 1


@pytest.mark.asyncio
async def test_mock_returns_no_usage():
    llm = MockLLMClient()
    result = await llm.parse_list(["arroz"])
    assert result.usage is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw, term, qty",
    [
        ("3 arroz", "arroz", 3),
        ("dois feijao", "feijao", 2),
        ("dúzia ovos", "ovos", 12),
        ("meia dúzia de ovos", "ovos", 6),
        ("um e meio kg arroz", "arroz", 2),
        ("2 e meio pacotes cafe", "cafe", 3),
        ("1,5 kg feijao", "feijao", 2),
        ("1/2 kg arroz", "arroz", 1),  # half is descriptive, one line
    ],
)
async def test_requested_quantity_parsing(raw, term, qty):
    llm = MockLLMClient()
    items = (await llm.parse_list([raw])).items
    assert len(items) == 1, items
    assert items[0].search_term.lower() == term
    assert items[0].quantity == qty


@pytest.mark.asyncio
async def test_fraction_not_split_into_two_items():
    # "1/2" must not be split like the item separator "arroz/feijão" is.
    llm = MockLLMClient()
    items = (await llm.parse_list(["1/2 kg arroz"])).items
    assert len(items) == 1
    items2 = (await llm.parse_list(["arroz/feijão"])).items
    assert {i.search_term.lower() for i in items2} == {"arroz", "feijão"}
