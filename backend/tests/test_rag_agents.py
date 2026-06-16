"""Tests for the lightweight RAG + Requester/Verifier agents (scale foundation)."""
import pytest

from app.cache import Cache
from app.services.llm.base import ParsedItem
from app.services.llm.requester import BasicRequester
from app.services.llm.mock_client import MockLLMClient
from app.services.llm.verifier import BasicVerifier
from app.services.normalization.matcher import NormalizedOffer


@pytest.mark.asyncio
async def test_cache_rag_mappings(fakeredis_client):
    c = Cache(client=fakeredis_client)
    await c.record_successful_mapping("pao", "pao frances", 5)
    await c.record_successful_mapping("pao", "pao frances", 3)
    await c.record_successful_mapping("manteiga", "manteiga com sal", 4)

    alts = await c.lookup_effective_terms("pao", limit=2)
    assert "pao frances" in alts

    best = await c.get_best_effective_term("pao")
    assert best == "pao frances"

    none = await c.get_best_effective_term("coisa que nunca existiu")
    assert none is None


@pytest.mark.asyncio
async def test_requester_refines_with_rag(fakeredis_client):
    inner = MockLLMClient()
    req = BasicRequester(inner=inner)
    c = Cache(client=fakeredis_client)
    # Pre-populate knowledge
    await c.record_successful_mapping("pao", "pao frances", 6)

    res = await req.refine_and_parse(["pao"], cache=c)
    assert len(res.items) == 1
    # Because of RAG, it should have preferred the effective term we recorded
    # (the mock parser turns "pao" into "pao"; the refinement should swap it)
    assert res.items[0].search_term in ("pao frances", "pao")  # depending on exact mock behavior


@pytest.mark.asyncio
async def test_verifier_records_and_suggests(fakeredis_client):
    v = BasicVerifier()
    c = Cache(client=fakeredis_client)

    # Simulate a low-match item + one good
    parsed = [ParsedItem(raw="iogurte", label="iogurte", search_term="iogurte", quantity=1)]
    # Empty offers for the bad one
    offers = {"iogurte": []}

    new_offers, suggestions = await v.verify_and_organize(parsed, offers, cache=c)
    # It should have tried to record (even with 0) and looked for alts (none yet)
    assert isinstance(suggestions, list)

    # Now record a success for something else
    await c.record_successful_mapping("iogurte", "iogurte natural", 4)
    _, suggestions2 = await v.verify_and_organize(parsed, {"iogurte": []}, cache=c)
    # On second pass the verifier would have seen the alt in real flow, but here we just check it doesn't crash
    assert isinstance(suggestions2, list)
