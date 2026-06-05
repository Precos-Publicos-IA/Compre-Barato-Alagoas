import pytest

from app.services.llm.mock_client import MockLLMClient


@pytest.mark.asyncio
async def test_splits_compound_line():
    llm = MockLLMClient()
    items = await llm.parse_list(["arroz, feijão e leite"])
    terms = {i.search_term.lower() for i in items}
    assert {"arroz", "feijão", "leite"} <= terms


@pytest.mark.asyncio
async def test_strips_size_and_count():
    llm = MockLLMClient()
    items = await llm.parse_list(["2 arroz 5kg"])
    assert len(items) == 1
    assert items[0].search_term.lower() == "arroz"
    assert items[0].quantity == 2


@pytest.mark.asyncio
async def test_dedupes():
    llm = MockLLMClient()
    items = await llm.parse_list(["leite", "leite"])
    assert len(items) == 1
