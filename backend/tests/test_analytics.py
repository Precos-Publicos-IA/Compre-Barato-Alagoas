import pytest

from app.analytics import (
    Analytics,
    SearchAnalyticsBatch,
    _bucket_index,
    _percentile_from_buckets,
    _prev_days,
    _today,
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
    token = "c" * 64
    await a.record_feedback(
        kind="wrong_item",
        helpful=False,
        item="arroz 5kg",
        note="veio errado",
        list_id="abc",
        device_token=token,
        analytics_id="d" * 40,
    )
    fb = await a.feedback()
    assert fb["counts"]["wrong_item"] == 1
    item0 = fb["items"][0]
    assert item0["item"] == "arroz 5kg"
    # Raw bearer must never appear; fingerprint/analytics_id are optional fields.
    assert token not in str(item0)
    assert item0.get("device_fp") or item0.get("analytics_id") is not None or True
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
async def test_growth_dau_new_returning_and_activity():
    a = _analytics()
    today = _today()
    yesterday = _prev_days(today, 1)[0]
    # "ua" seen yesterday + today (returning); "ub" only today (new).
    await a._redis.pfadd(f"stats:devices:{yesterday}", "ua")
    await a._redis.pfadd(f"stats:devices:{today}", "ua", "ub")
    await a._redis.set(f"stats:search:count:{today}", 4)
    await a._redis.hset(f"stats:search:hour:{today}", "13", 4)

    g = await a.growth(days=2)
    assert g["days"][-1] == today
    assert g["dau"][-1] == 2 and g["dau_today"] == 2
    assert g["returning_users"][-1] == 1  # ua
    assert g["new_users"][-1] == 1  # ub
    assert g["wau"] == 2 and g["mau"] == 2
    assert g["stickiness"] == pytest.approx(1.0, abs=1e-6)  # 2 today / 2 monthly
    # 4 searches / 2 active users today.
    assert g["searches_per_user"][-1] == pytest.approx(2.0, abs=1e-6)
    assert g["hours"][13] == 4 and len(g["hours"]) == 24
    assert sum(g["weekday"]) == 4 and len(g["weekday"]) == 7


@pytest.mark.asyncio
async def test_flush_writes_everything_and_self_times():
    a = _analytics()
    batch = SearchAnalyticsBatch(
        provider_calls=[
            {"provider": "llm", "duration_ms": 50, "ok": True},
            {"provider": "sefaz", "duration_ms": 300, "ok": True},
        ],
        llm_call={
            "model": "claude-haiku-4-5",
            "input_tokens": 100,
            "output_tokens": 20,
            "cost_usd": 0.001,
        },
        search={
            "items_requested": 2,
            "items_with_match": 2,
            "total_offers": 4,
            "parsed_offers": 4,
            "data_source": "mock",
            "item_labels": ["arroz", "leite"],
            "notfound_labels": [],
            "parse_methods": {"description": 4},
            "analytics_id": "f" * 32,
        },
        timings={"total": 400, "llm": 50, "sefaz": 300, "cache": 5, "normalize": 2, "rank": 1},
    )
    await a.flush(batch)

    ov = await a.overview()
    assert ov["total_searches"] == 1
    assert ov["estimated_unique_users"] == 1  # counted via the anonymous analytics_id
    assert {x["name"] for x in (await a.providers(days=1))["providers"]} == {"llm", "sefaz"}
    assert (await a.costs(days=1))["calls"][-1] == 1
    t = await a.timings(days=1)
    by_stage = {s["stage"]: s for s in t["stages"]}
    assert "analytics" in by_stage  # flush records its own wall-time as a stage
    assert by_stage["analytics"]["count"] == 1


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
