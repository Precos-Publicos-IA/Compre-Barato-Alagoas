import pytest

from app.analytics import (
    Analytics,
    _bucket_index,
    _percentile_from_buckets,
)
from app.cache import Cache


def _analytics() -> Analytics:
    # fakeredis is patched in via the autouse fixture; reuse the Cache client.
    return Analytics(client=Cache(redis_url="redis://test").redis)


@pytest.mark.asyncio
async def test_record_search_feeds_overview_and_quality():
    a = _analytics()
    await a.record_search(
        items_requested=3,
        items_with_match=2,
        total_offers=10,
        parsed_offers=8,
        data_source="mock",
        item_labels=["arroz", "leite", "pão"],
        notfound_labels=["pão"],
        parse_methods={"unidade_medida": 4, "description": 6},
        device_token="a" * 32,
    )

    ov = await a.overview()
    assert ov["total_searches"] == 1
    assert ov["overall_match_rate"] == pytest.approx(2 / 3, abs=1e-3)
    assert ov["overall_quantity_parse_rate"] == pytest.approx(0.8, abs=1e-3)
    assert ov["estimated_unique_users"] == 1

    q = await a.quality(days=1)
    assert q["search_counts"][-1] == 1
    assert q["parse_method_distribution"]["description"] == 6

    items = await a.items(days=1)
    searched = {i["label"]: i["count"] for i in items["top_searched"]}
    notfound = {i["label"]: i["count"] for i in items["top_not_found"]}
    assert searched["arroz"] == 1
    assert notfound == {"pão": 1}

    recent = await a.recent_searches()
    assert recent and recent[0]["source"] == "mock"


@pytest.mark.asyncio
async def test_record_llm_call_feeds_costs():
    a = _analytics()
    await a.record_llm_call(
        model="claude-haiku-4-5",
        input_tokens=1000,
        output_tokens=200,
        cost_usd=0.002,
    )
    costs = await a.costs(days=1)
    assert costs["calls"][-1] == 1
    assert costs["input_tokens"][-1] == 1000
    assert costs["cost_usd"][-1] == pytest.approx(0.002, abs=1e-9)
    assert costs["per_model"][0]["model"] == "claude-haiku-4-5"
    assert costs["per_model"][0]["output_tokens"] == 200

    ov = await a.overview()
    assert ov["total_llm_cost_usd"] == pytest.approx(0.002, abs=1e-6)


@pytest.mark.asyncio
async def test_record_feedback():
    a = _analytics()
    await a.record_feedback(
        kind="wrong_item",
        helpful=False,
        item="arroz 5kg",
        note="veio errado",
        list_id="abc",
    )
    fb = await a.feedback()
    assert fb["counts"]["wrong_item"] == 1
    assert fb["items"][0]["item"] == "arroz 5kg"
    # Filtering by kind keeps only matches.
    assert (await a.feedback(kind="helpful"))["items"] == []


def test_bucket_and_percentile_helpers():
    # Buckets bound: (50,100,250,500,1000,2000,4000,8000) + overflow.
    assert _bucket_index(10) == 0
    assert _bucket_index(50) == 0
    assert _bucket_index(51) == 1
    assert _bucket_index(9000) == 8  # overflow
    # 8 samples in the 250ms bucket → both p50 and p95 land at 250ms.
    buckets = [0, 0, 8, 0, 0, 0, 0, 0, 0]
    assert _percentile_from_buckets(buckets, 0.5) == 250.0
    assert _percentile_from_buckets(buckets, 0.95) == 250.0
    assert _percentile_from_buckets([0] * 9, 0.5) == 0.0


@pytest.mark.asyncio
async def test_record_timings_feeds_timings():
    a = _analytics()
    await a.record_timings(
        {"total": 1200, "llm": 300, "sefaz": 700, "cache": 20, "normalize": 5, "rank": 2}
    )
    await a.record_timings(
        {"total": 400, "llm": 100, "sefaz": 250, "cache": 10, "normalize": 3, "rank": 1}
    )
    t = await a.timings(days=1)
    stages = {s["stage"]: s for s in t["stages"]}
    assert stages["total"]["count"] == 2
    assert stages["total"]["avg_ms"] == pytest.approx(800.0, abs=0.1)
    # Two totals (1200, 400) → p95 lands in the 2000ms bucket, p50 in 500ms.
    assert stages["total"]["p95_ms"] == 2000.0
    assert stages["total"]["p50_ms"] == 500.0
    assert sum(t["distribution"]) == 2
    assert t["total_series"]["count"][-1] == 2
    assert t["total_series"]["avg_ms"][-1] == pytest.approx(800.0, abs=0.1)


@pytest.mark.asyncio
async def test_record_provider_call_feeds_providers():
    a = _analytics()
    await a.record_provider_call(provider="sefaz", duration_ms=600, ok=True)
    await a.record_provider_call(provider="sefaz", duration_ms=900, ok=False)
    await a.record_provider_call(provider="llm", duration_ms=120, ok=True)
    p = await a.providers(days=1)
    by_name = {x["name"]: x for x in p["providers"]}
    assert by_name["sefaz"]["calls"] == 2
    assert by_name["sefaz"]["errors"] == 1
    assert by_name["sefaz"]["error_rate"] == pytest.approx(0.5, abs=1e-3)
    assert by_name["sefaz"]["last_error_ts"]
    assert by_name["sefaz"]["avg_ms"] == pytest.approx(750.0, abs=0.1)
    assert by_name["llm"]["error_rate"] == 0.0
    assert by_name["llm"]["last_ok_ts"]
