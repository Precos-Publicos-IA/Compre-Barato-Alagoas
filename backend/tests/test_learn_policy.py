"""Phase 3 learn_policy tests — single door for RAG mutations (3-S2…3-S8)."""

from __future__ import annotations

import inspect

import pytest

from app.cache import Cache
from app.services.rag import learn_policy
from app.services.rag.learn_policy import (
    ENV_MATCH_LEARN,
    learning_enabled,
    on_search_item_result,
    on_user_feedback,
)
from app.services.rag.store import RAGStore


def _rag() -> RAGStore:
    return RAGStore(redis=Cache(redis_url="redis://test").redis)


# --- 3-S2: fetch_failed never success-learns ---------------------------------


@pytest.mark.asyncio
async def test_s2_fetch_failed_refuses_success(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    result = await on_search_item_result(
        rag,
        user_term="arroz",
        effective_search_term="arroz",
        offers_found=5,
        fetch_failed=True,
        score=0.9,
        best_description="ARROZ TIPO 1 5KG",
        package_class_ok=True,
    )
    assert result.action == "refused_fetch_failed"
    assert await rag.lookup_effective_terms("arroz", limit=3) == []


# --- 3-S3: heads-incompatible rewrite refused --------------------------------


@pytest.mark.asyncio
async def test_s3_peito_ovos_never_stored(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    result = await on_search_item_result(
        rag,
        user_term="peito de frango",
        effective_search_term="ovos",
        offers_found=10,
        fetch_failed=False,
        score=0.99,
        best_description="OVOS BRANCOS BANDEJA C/12",
        package_class_ok=True,
    )
    assert result.action == "refused_heads"
    assert await rag.lookup_effective_terms("peito de frango", limit=3) == []


@pytest.mark.asyncio
async def test_s3_queijo_pao_de_queijo_never_stored(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    result = await on_search_item_result(
        rag,
        user_term="queijo",
        effective_search_term="pao de queijo",
        offers_found=8,
        fetch_failed=False,
        score=0.9,
        best_description="PAO DE QUEIJO CONGELADO 1KG",
        package_class_ok=True,
    )
    assert result.action == "refused_heads"
    assert await rag.lookup_effective_terms("queijo", limit=3) == []


# --- 3-S4: alignment reject refuses success ----------------------------------


@pytest.mark.asyncio
async def test_s4_alignment_reject_refuses(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    # Compatible rewrite term, but best description is modifier pollution.
    result = await on_search_item_result(
        rag,
        user_term="queijo",
        effective_search_term="queijo",
        offers_found=3,
        fetch_failed=False,
        score=0.85,
        best_description="PAO DE QUEIJO MINI",
        package_class_ok=True,
    )
    assert result.action == "refused_alignment"
    assert await rag.lookup_effective_terms("queijo", limit=3) == []


# --- 3-S5: score below min_score_to_learn refuses ----------------------------


@pytest.mark.asyncio
async def test_s5_low_score_refuses(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    result = await on_search_item_result(
        rag,
        user_term="arroz",
        effective_search_term="arroz",
        offers_found=2,
        fetch_failed=False,
        score=0.40,  # < 0.50 default
        best_description="ARROZ TIPO 1 5KG",
        package_class_ok=True,
    )
    assert result.action == "refused_score"
    assert await rag.lookup_effective_terms("arroz", limit=3) == []


@pytest.mark.asyncio
async def test_s5_package_class_false_refuses(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    result = await on_search_item_result(
        rag,
        user_term="oleo",
        effective_search_term="oleo",
        offers_found=2,
        fetch_failed=False,
        score=0.80,
        best_description="OLEO DE COCO 200ML",
        package_class_ok=False,
    )
    assert result.action == "refused_package_class"
    assert await rag.lookup_effective_terms("oleo", limit=3) == []


# --- 3-S6: happy path accepts and stores mapping -----------------------------


@pytest.mark.asyncio
async def test_s6_happy_path_arroz_stores_mapping(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    result = await on_search_item_result(
        rag,
        user_term="arroz",
        effective_search_term="arroz tipo 1",
        offers_found=4,
        fetch_failed=False,
        score=0.75,
        best_description="ARROZ TIPO 1 CAMIL 5KG",
        package_class_ok=True,
    )
    assert result.action == "success", result
    alts = await rag.lookup_effective_terms("arroz", limit=3)
    assert any("arroz" in a for a in alts)
    assert "arroz tipo 1" in alts or alts[0].startswith("arroz")


# --- 3-S7: wrong_item demotes and never success ------------------------------


@pytest.mark.asyncio
async def test_s7_wrong_item_demotes_never_success(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    # Seed a mapping first.
    seed = await on_search_item_result(
        rag,
        user_term="pao",
        effective_search_term="pao frances",
        offers_found=6,
        fetch_failed=False,
        score=0.8,
        best_description="PAO FRANCES UN",
        package_class_ok=True,
    )
    assert seed.action == "success"
    assert "pao frances" in await rag.lookup_effective_terms("pao", limit=3)

    # Track that record_success is not called during feedback.
    calls: list[tuple] = []
    orig = rag.record_success

    async def _spy(*a, **k):
        calls.append((a, k))
        return await orig(*a, **k)

    rag.record_success = _spy  # type: ignore[method-assign]

    fb = await on_user_feedback(
        rag,
        kind="wrong_item",
        query="pao",
        description="PAO DOCE RECHEADO",
        effective_search_term="pao frances",
    )
    assert fb.action == "demote"
    assert calls == [], "wrong_item must never call record_success"
    assert await rag.lookup_effective_terms("pao", limit=3) == []

    # Miss signal should be present.
    miss_score = await rag.redis.zscore("rag:miss:pao", "pao frances")
    assert miss_score is not None and float(miss_score) >= 1.0


# --- 3-S8: MATCH_LEARN=0 no-op writes ----------------------------------------


@pytest.mark.asyncio
async def test_s8_match_learn_off_no_writes(monkeypatch):
    monkeypatch.setenv(ENV_MATCH_LEARN, "0")
    assert not learning_enabled()
    rag = _rag()

    result = await on_search_item_result(
        rag,
        user_term="arroz",
        effective_search_term="arroz",
        offers_found=5,
        fetch_failed=False,
        score=0.9,
        best_description="ARROZ TIPO 1 5KG",
        package_class_ok=True,
    )
    assert result.action == "refused_disabled"
    assert await rag.lookup_effective_terms("arroz", limit=3) == []

    # Seed with learning re-enabled, then demote with learn off.
    monkeypatch.setenv(ENV_MATCH_LEARN, "1")
    await on_search_item_result(
        rag,
        user_term="cafe",
        effective_search_term="cafe torrado",
        offers_found=3,
        fetch_failed=False,
        score=0.85,
        best_description="CAFE TORRADO MOIDO 500G",
        package_class_ok=True,
    )
    assert await rag.lookup_effective_terms("cafe", limit=1)

    monkeypatch.setenv(ENV_MATCH_LEARN, "0")
    fb = await on_user_feedback(
        rag,
        kind="wrong_item",
        query="cafe",
        effective_search_term="cafe torrado",
    )
    assert fb.action == "refused_disabled"
    # Mapping still present — demote was a no-op.
    assert "cafe torrado" in await rag.lookup_effective_terms("cafe", limit=3)


# --- 3-S1 support: verifier does not call record_success directly ------------


def test_s1_verifier_uses_learn_policy_not_direct_record_success():
    from app.services.llm import verifier as ver_mod

    src = inspect.getsource(ver_mod)
    assert "on_search_item_result" in src
    assert "learn_policy" in src or "on_search_item_result" in src
    # No direct store write from verifier body.
    assert "await rag.record_success" not in src
    assert "await rag.record_miss" not in src


def test_s1_learn_policy_is_the_production_door():
    """Production modules under app/ should not call record_success outside policy."""
    import pathlib

    root = pathlib.Path(learn_policy.__file__).resolve().parents[2]  # app/
    offenders: list[str] = []
    allow = {
        "services/rag/store.py",  # primitive
        "services/rag/learn_policy.py",  # the door
        "cache.py",  # thin prewarm/legacy wrapper → store (not search hot path)
    }
    for path in root.rglob("*.py"):
        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel in allow or "/__pycache__/" in rel:
            continue
        text = path.read_text(encoding="utf-8")
        if "record_success(" in text and "learn_policy" not in rel:
            # Allow comments / strings about record_success without calls?
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
                    continue
                if "record_success(" in line and "def record_success" not in line:
                    offenders.append(f"{rel}:{i}:{stripped[:80]}")
    assert offenders == [], f"rogue record_success call sites: {offenders}"


def test_s1_feedback_route_uses_on_user_feedback():
    """3-S1 / 3-S7: POST /feedback wrong_item funnels through learn_policy."""
    from app.api.routes import feedback as fb_mod

    src = inspect.getsource(fb_mod)
    assert "on_user_feedback" in src
    assert "wrong_item" in src


# --- miss path + empty offers -------------------------------------------------


@pytest.mark.asyncio
async def test_zero_offers_records_miss_not_success(monkeypatch):
    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()
    result = await on_search_item_result(
        rag,
        user_term="wasabi",
        effective_search_term="wasabi",
        offers_found=0,
        fetch_failed=False,
    )
    assert result.action == "miss"
    assert await rag.lookup_effective_terms("wasabi", limit=3) == []
    miss = await rag.redis.zscore("rag:miss:wasabi", "wasabi")
    assert miss is not None


@pytest.mark.asyncio
async def test_verifier_funnel_happy_and_poison(monkeypatch):
    """Integration: BasicVerifier → learn_policy for success; poison refused."""
    from app.services.llm.base import ParsedItem
    from app.services.llm.verifier import BasicVerifier
    from app.services.normalization.matcher import NormalizedOffer

    monkeypatch.delenv(ENV_MATCH_LEARN, raising=False)
    rag = _rag()

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

    v = BasicVerifier()
    # Happy path: arroz with in-class description
    out = await v.verify_and_organize(
        [ParsedItem(raw="arroz", label="arroz", search_term="arroz", quantity=1)],
        {"arroz": [_offer("ARROZ TIPO 1 CAMIL 5KG", 22.0)]},
        rag=rag,
    )
    assert out.rag_successes >= 1
    assert await rag.lookup_effective_terms("arroz", limit=1)

    # Poison path: peito searching as ovos must not learn
    out2 = await v.verify_and_organize(
        [
            ParsedItem(
                raw="peito de frango",
                label="peito de frango",
                search_term="ovos",
                quantity=1,
            )
        ],
        {
            "peito de frango": [
                _offer("OVOS BRANCOS BANDEJA C/12", 12.0),
            ]
        },
        rag=rag,
    )
    # Offers likely dropped by relevance; either way no peito→ovos mapping.
    assert await rag.lookup_effective_terms("peito de frango", limit=3) == []
    assert out2.rag_successes == 0
