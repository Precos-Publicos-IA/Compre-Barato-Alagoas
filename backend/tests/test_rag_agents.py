"""Tests for RAG + Requester/Verifier/Orchestrator (cost-first agent pipeline)."""
import pytest

from app.cache import Cache
from app.services.llm.base import ParsedItem
from app.services.llm.requester import BasicRequester
from app.services.llm.mock_client import MockLLMClient
from app.services.llm.verifier import BasicVerifier
from app.services.llm.orchestrator import SearchOrchestrator
from app.services.rag.store import RAGStore
from app.services.rag.relevance import score_offer, filter_offers
from app.services.normalization.matcher import NormalizedOffer


def _offer(desc: str, price: float = 5.0) -> NormalizedOffer:
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
        cnpj="web:1",
        store_name="Loja",
        latitude=None,
        longitude=None,
        bairro=None,
        address=None,
    )


from app.services.rag.store import rewrite_compatible, filter_compatible_terms


def test_rewrite_compatible_blocks_cross_class_poison():
    """Honest eval root cause: peito/queijo/… → ovos; salsicha→sal; papel→toalha."""
    assert rewrite_compatible("pao", "pao frances")
    assert rewrite_compatible("ovo", "ovos")
    assert rewrite_compatible("ovos", "ovos brancos")
    assert not rewrite_compatible("peito de frango", "ovos")
    assert not rewrite_compatible("farinha de trigo", "ovos")
    assert not rewrite_compatible("queijo", "ovos")
    assert not rewrite_compatible("água sanitária", "ovos")
    assert not rewrite_compatible("salsicha", "sal")
    assert not rewrite_compatible("salgadinho", "sal")
    assert not rewrite_compatible("sabão em pó", "leite")
    assert not rewrite_compatible("papel higiênico", "papel toalha")
    assert rewrite_compatible("papel higiênico", "papel higienico")
    # Head order matters: "frango peito" flips head to frango → rejected systemically.
    assert filter_compatible_terms(
        "peito de frango", ["ovos", "peito frango", "frango peito"]
    ) == ["peito frango"]


@pytest.mark.asyncio
async def test_cache_rag_mappings():
    c = Cache(redis_url="redis://localhost:6379/0")
    await c.record_successful_mapping("pao", "pao frances", 5)
    await c.record_successful_mapping("pao", "pao frances", 3)
    await c.record_successful_mapping("manteiga", "manteiga com sal", 4)

    alts = await c.lookup_effective_terms("pao", limit=2)
    assert "pao frances" in alts
    assert await c.get_best_effective_term("pao") == "pao frances"


@pytest.mark.asyncio
async def test_rag_store_similar_terms():
    redis = Cache(redis_url="redis://localhost:6379/0").redis
    rag = RAGStore(redis=redis)
    await rag.record_success("pao frances", "pao frances", 5)
    await rag.record_success("pao de forma", "pao de forma", 3)
    sims = await rag.find_similar_effective_terms("pao", limit=3, min_overlap=1)
    assert any("pao" in s for s in sims)


@pytest.mark.asyncio
async def test_rag_refuses_and_hides_egg_poison_mappings():
    redis = Cache(redis_url="redis://localhost:6379/0").redis
    rag = RAGStore(redis=redis)
    # Direct poison write attempt must be refused.
    await rag.record_success("peito de frango", "ovos", 99)
    assert await rag.lookup_effective_terms("peito de frango", limit=3) == []
    # Inject poison via raw Redis (simulates pre-fix production keys).
    await redis.zincrby("rag:effective_for:peito de frango", 50.0, "ovos")
    await redis.zincrby("rag:effective_for:queijo", 50.0, "ovos")
    assert await rag.lookup_effective_terms("peito de frango", limit=3) == []
    assert await rag.lookup_effective_terms("queijo", limit=3) == []
    # Compatible mapping still works.
    await rag.record_success("peito de frango", "peito de frango", 4)
    alts = await rag.lookup_effective_terms("peito de frango", limit=3)
    assert alts and all("ovo" not in a for a in alts)


@pytest.mark.asyncio
async def test_requester_does_not_rewrite_to_ovos():
    inner = MockLLMClient()
    req = BasicRequester(inner=inner)
    c = Cache(redis_url="redis://localhost:6379/0")
    # Poison keys in Redis
    await c.redis.zincrby("rag:effective_for:peito de frango", 99.0, "ovos")
    await c.redis.zincrby("rag:effective_for:farinha de trigo", 99.0, "ovos")
    res = await req.refine_and_parse(["peito de frango", "farinha de trigo"], cache=c)
    for item in res.items:
        assert "ovo" not in (item.search_term or "").lower()


@pytest.mark.asyncio
async def test_requester_refines_with_rag():
    inner = MockLLMClient()
    req = BasicRequester(inner=inner)
    c = Cache(redis_url="redis://localhost:6379/0")
    await c.record_successful_mapping("pao", "pao frances", 6)

    res = await req.refine_and_parse(["pao"], cache=c)
    assert len(res.items) == 1
    assert res.items[0].search_term in ("pao frances", "pao")


@pytest.mark.asyncio
async def test_verifier_records_and_suggests_retry():
    v = BasicVerifier()
    c = Cache(redis_url="redis://localhost:6379/0")
    await c.record_successful_mapping("iogurte", "iogurte natural", 4)

    parsed = [
        ParsedItem(raw="iogurte", label="iogurte", search_term="iogurte", quantity=1)
    ]
    outcome = await v.verify_and_organize(parsed, {"iogurte": []}, cache=c)
    assert outcome.retry_terms.get("iogurte") == "iogurte natural"
    assert any("iogurte natural" in s for s in outcome.suggestions)


def test_relevance_downranks_pet_food():
    rice = _offer("ARROZ TIO JOAO TIPO 1 5KG", 25)
    pet = _offer("ARROZ P CAES LUPPY 5KG", 15)
    assert score_offer("arroz", "arroz", rice) > score_offer("arroz", "arroz", pet)
    rel = filter_offers("arroz", "arroz", [pet, rice], min_score=0.15)
    assert rel.kept[0].description == rice.description


@pytest.mark.asyncio
async def test_orchestrator_uses_rag_then_fetch():
    """End-to-end: Requester rewrites via RAG, fetch returns offers, no crash."""
    c = Cache(redis_url="redis://localhost:6379/0")
    rag = RAGStore(redis=c.redis)
    await rag.record_success("pao", "pao frances", 8)

    calls: list[str] = []

    async def fetch(term: str, label: str):
        calls.append(term)
        if "pao" in term:
            return [_offer("PAO FRANCES KG", 1.5)]
        return []

    orch = SearchOrchestrator(llm=MockLLMClient(), rag=rag)
    result = await orch.run(["pao"], fetch_offers=fetch)
    assert calls, "fetch must be called"
    assert any(result.offers_by_item.values()), "expected offers after RAG+fetch"


@pytest.mark.asyncio
async def test_orchestrator_retry_when_first_term_empty():
    """Verifier requests one re-fetch when first term misses but an alt exists.

    Seed RAG under a *different* key than the mock's search_term so the Requester
    does not rewrite on the first pass; only the Verifier finds the alt after a miss.
    Alt must be rewrite-compatible (shared content token) — cross-class alts are refused.
    """
    c = Cache(redis_url="redis://localhost:6379/0")
    rag = RAGStore(redis=c.redis)
    await rag.record_success("iogurte", "iogurte natural", 5)

    calls: list[str] = []

    async def fetch(term: str, label: str):
        calls.append(term)
        if "natural" in term:
            return [_offer("IOGURTE NATURAL 170G", 3.0)]
        return []

    from app.services.llm.base import ParseResult

    class StubLLM:
        source_name = "stub"

        async def parse_list(self, raw_items):
            return ParseResult(
                items=[
                    ParsedItem(
                        raw="iogurte",
                        label="iogurte",
                        search_term="iogurte xpto",
                        quantity=1,
                    )
                ],
                usage=None,
            )

    orch = SearchOrchestrator(llm=StubLLM(), rag=rag)  # type: ignore[arg-type]
    result = await orch.run(["iogurte"], fetch_offers=fetch)
    # Requester may rewrite on first pass via RAG, or Verifier may retry — either path
    # must land on the known-good term and return offers.
    assert any("natural" in c for c in calls)
    assert result.offers_by_item["iogurte"]
