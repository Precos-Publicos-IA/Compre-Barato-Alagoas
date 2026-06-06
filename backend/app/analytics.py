"""Product/AI analytics, stored Redis-native (no extra database).

Everything the admin dashboard shows is derived from a handful of Redis structures
written on the search hot path. Lean into Redis (CLAUDE.md): plain counters for
totals, hashes for per-model / per-hour breakdowns, sorted sets for "top items",
HyperLogLog for the unique-user estimate, and capped Streams for the recent
search/feedback feeds.

Writes are **best-effort**: every method swallows and logs failures so analytics can
never break a user-facing search. Day buckets are ``YYYYMMDD`` in UTC.

Privacy (LGPD): the device token is a bearer credential — it is never logged or
stored. The unique-user estimate adds only a salted hash of the token to a
HyperLogLog (aggregate cardinality, no per-device row, not reversible).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Keep the recent-activity feeds bounded; older entries are trimmed automatically.
_STREAM_MAXLEN = 1000
# Salt the device-token hash before it enters the HyperLogLog (defence in depth).
_DEVICE_SALT = "compre-barato-alagoas/analytics/v1"
# Feedback kinds we keep running totals for.
FEEDBACK_KINDS = ("helpful", "wrong_item", "other")

# Latency histogram bucket upper bounds, in milliseconds. A sample is counted in
# the first bucket whose bound it does not exceed; anything above the last bound
# lands in an extra overflow bucket (index == len(_LATENCY_BUCKETS_MS)). These give
# cheap, Redis-native p50/p95 estimates without storing per-request samples.
_LATENCY_BUCKETS_MS = (50, 100, 250, 500, 1000, 2000, 4000, 8000)
_N_BUCKETS = len(_LATENCY_BUCKETS_MS) + 1  # +1 overflow
# Subsystem stages timed per search (goals: user wait time + subsystem health).
TIMING_STAGES = ("total", "llm", "sefaz", "cache", "normalize", "rank")


def _bucket_index(ms: float) -> int:
    for i, hi in enumerate(_LATENCY_BUCKETS_MS):
        if ms <= hi:
            return i
    return len(_LATENCY_BUCKETS_MS)  # overflow


def _percentile_from_buckets(buckets: list[int], pct: float) -> float:
    """Coarse percentile (ms) from histogram bucket counts.

    Returns the upper bound of the bucket the percentile falls in (the overflow
    bucket reports 2× the last bound). Clearly an estimate — fine for spotting
    "users wait ~2s" vs "~8s" on a low-traffic app.
    """
    total = sum(buckets)
    if total == 0:
        return 0.0
    target = total * pct
    cum = 0
    for i, count in enumerate(buckets):
        cum += count
        if cum >= target:
            if i < len(_LATENCY_BUCKETS_MS):
                return float(_LATENCY_BUCKETS_MS[i])
            return float(_LATENCY_BUCKETS_MS[-1] * 2)
    return float(_LATENCY_BUCKETS_MS[-1] * 2)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _last_days(n: int) -> list[str]:
    """Day buckets for the last ``n`` days, oldest first (inclusive of today)."""
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(n - 1, -1, -1)]


class Analytics:
    def __init__(self, *, client: Any) -> None:
        self._redis = client

    # --- write path --------------------------------------------------------

    async def record_search(
        self,
        *,
        items_requested: int,
        items_with_match: int,
        total_offers: int,
        parsed_offers: int,
        data_source: str,
        item_labels: list[str],
        notfound_labels: list[str],
        parse_methods: dict[str, int],
        device_token: str | None = None,
        approx_region: str | None = None,
    ) -> None:
        day = _today()
        hour = datetime.now(timezone.utc).strftime("%H")
        try:
            pipe = self._redis.pipeline()
            for scope in (day, "total"):
                pipe.incr(f"stats:search:count:{scope}")
                pipe.incrby(f"stats:search:items_req:{scope}", items_requested)
                pipe.incrby(f"stats:search:matched:{scope}", items_with_match)
                pipe.incrby(f"stats:search:offers:{scope}", total_offers)
                pipe.incrby(f"stats:search:parsed:{scope}", parsed_offers)
                pipe.incr(f"stats:search:source:{data_source}:{scope}")
            pipe.hincrby(f"stats:search:hour:{day}", hour, 1)
            for method, count in parse_methods.items():
                if count:
                    pipe.incrby(f"stats:parsemethod:{method}:{day}", count)
                    pipe.incrby(f"stats:parsemethod:{method}:total", count)
            for label in item_labels:
                pipe.zincrby(f"stats:items:searched:{day}", 1, label)
            for label in notfound_labels:
                pipe.zincrby(f"stats:items:notfound:{day}", 1, label)
            if device_token:
                h = hashlib.sha256(
                    (_DEVICE_SALT + device_token).encode()
                ).hexdigest()
                pipe.pfadd(f"stats:devices:{day}", h)
                pipe.pfadd("stats:devices:total", h)
            fields = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "n_items": str(items_requested),
                "matched": str(items_with_match),
                "source": data_source,
                "region": approx_region or "",
            }
            pipe.xadd("events:search", fields, maxlen=_STREAM_MAXLEN, approximate=True)
            await pipe.execute()
        except Exception:  # pragma: no cover - analytics never breaks search
            logger.exception("record_search failed")

    async def record_llm_call(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> None:
        day = _today()
        try:
            pipe = self._redis.pipeline()
            pipe.sadd("stats:llm:models", model)
            for scope in (day, "total"):
                pipe.incr(f"stats:llm:calls:{scope}")
                pipe.incrby(f"stats:llm:in_tok:{scope}", input_tokens)
                pipe.incrby(f"stats:llm:out_tok:{scope}", output_tokens)
                pipe.incrbyfloat(f"stats:llm:cost:{scope}", cost_usd)
            mkey = f"stats:llm:model:{model}:{day}"
            pipe.hincrby(mkey, "calls", 1)
            pipe.hincrby(mkey, "in_tok", input_tokens)
            pipe.hincrby(mkey, "out_tok", output_tokens)
            pipe.hincrbyfloat(mkey, "cost", cost_usd)
            await pipe.execute()
        except Exception:  # pragma: no cover
            logger.exception("record_llm_call failed")

    async def record_feedback(
        self,
        *,
        kind: str,
        helpful: bool | None,
        item: str | None,
        note: str | None,
        list_id: str | None,
    ) -> None:
        day = _today()
        try:
            pipe = self._redis.pipeline()
            fields = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "kind": kind,
                "helpful": "" if helpful is None else ("1" if helpful else "0"),
                "item": item or "",
                "note": note or "",
                "list_id": list_id or "",
            }
            pipe.xadd("events:feedback", fields, maxlen=_STREAM_MAXLEN, approximate=True)
            pipe.incr(f"stats:feedback:{kind}:{day}")
            pipe.incr(f"stats:feedback:{kind}:total")
            await pipe.execute()
        except Exception:  # pragma: no cover
            logger.exception("record_feedback failed")

    async def record_timings(self, stages: dict[str, float]) -> None:
        """Record per-search stage latencies (ms) into per-day + all-time histograms.

        ``stages`` maps a stage name (``TIMING_STAGES``) to its duration in ms for
        this one search. Feeds the "Desempenho" admin tab: ``total`` is the full
        response time the user waits for; the rest break it down per subsystem.
        """
        day = _today()
        try:
            pipe = self._redis.pipeline()
            for stage, ms in stages.items():
                b = _bucket_index(ms)
                for scope in (day, "total"):
                    key = f"stats:timing:{stage}:{scope}"
                    pipe.hincrby(key, "count", 1)
                    pipe.hincrbyfloat(key, "sum_ms", float(ms))
                    pipe.hincrby(key, f"b{b}", 1)
            await pipe.execute()
        except Exception:  # pragma: no cover - analytics never breaks search
            logger.exception("record_timings failed")

    async def record_provider_call(
        self, *, provider: str, duration_ms: float, ok: bool
    ) -> None:
        """Record one call to an external provider (``sefaz`` or ``llm``).

        Tracks latency (histogram) and failures so the admin "Provedores" tab can
        show error rate + p95 per third party — the signal for adjusting caching /
        query volume when a provider degrades.
        """
        day = _today()
        b = _bucket_index(duration_ms)
        now = datetime.now(timezone.utc).isoformat()
        try:
            pipe = self._redis.pipeline()
            pipe.sadd("stats:providers", provider)
            for scope in (day, "total"):
                key = f"stats:provider:{provider}:{scope}"
                pipe.hincrby(key, "calls", 1)
                pipe.hincrbyfloat(key, "sum_ms", float(duration_ms))
                pipe.hincrby(key, f"b{b}", 1)
                if not ok:
                    pipe.hincrby(key, "errors", 1)
            tkey = f"stats:provider:{provider}:total"
            pipe.hset(tkey, "last_ok_ts" if ok else "last_error_ts", now)
            await pipe.execute()
        except Exception:  # pragma: no cover
            logger.exception("record_provider_call failed")

    # --- read path (admin dashboard) --------------------------------------

    async def _get_int(self, key: str) -> int:
        v = await self._redis.get(key)
        try:
            return int(v) if v is not None else 0
        except (TypeError, ValueError):
            return 0

    async def _get_float(self, key: str) -> float:
        v = await self._redis.get(key)
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _dec(value: Any) -> Any:
        # Real Redis (decode_responses=True) yields str; fakeredis can yield bytes
        # from hgetall/smembers — normalize so str-keyed access works everywhere.
        return value.decode() if isinstance(value, bytes) else value

    @classmethod
    def _decode_map(cls, mapping: dict[Any, Any]) -> dict[str, str]:
        return {cls._dec(k): cls._dec(v) for k, v in mapping.items()}

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 3) if denominator else 0.0

    async def overview(self) -> dict[str, Any]:
        total_searches = await self._get_int("stats:search:count:total")
        today_searches = await self._get_int(f"stats:search:count:{_today()}")
        total_cost = await self._get_float("stats:llm:cost:total")
        matched = await self._get_int("stats:search:matched:total")
        items_req = await self._get_int("stats:search:items_req:total")
        offers = await self._get_int("stats:search:offers:total")
        parsed = await self._get_int("stats:search:parsed:total")
        try:
            unique_users = int(await self._redis.pfcount("stats:devices:total"))
        except Exception:  # pragma: no cover
            unique_users = 0
        hours_raw = self._decode_map(
            await self._redis.hgetall(f"stats:search:hour:{_today()}")
        )
        hours = [int(hours_raw.get(f"{h:02d}", 0) or 0) for h in range(24)]
        return {
            "total_searches": total_searches,
            "today_searches": today_searches,
            "estimated_unique_users": unique_users,
            "total_llm_cost_usd": round(total_cost, 4),
            "avg_cost_per_search_usd": (
                round(total_cost / total_searches, 6) if total_searches else 0.0
            ),
            "overall_match_rate": self._rate(matched, items_req),
            "overall_quantity_parse_rate": self._rate(parsed, offers),
            "hours_today": hours,
        }

    async def quality(self, days: int = 14) -> dict[str, Any]:
        buckets = _last_days(days)
        out: dict[str, Any] = {
            "days": buckets,
            "search_counts": [],
            "match_rate": [],
            "quantity_parse_rate": [],
        }
        for day in buckets:
            count = await self._get_int(f"stats:search:count:{day}")
            matched = await self._get_int(f"stats:search:matched:{day}")
            items_req = await self._get_int(f"stats:search:items_req:{day}")
            offers = await self._get_int(f"stats:search:offers:{day}")
            parsed = await self._get_int(f"stats:search:parsed:{day}")
            out["search_counts"].append(count)
            out["match_rate"].append(self._rate(matched, items_req))
            out["quantity_parse_rate"].append(self._rate(parsed, offers))
        methods: dict[str, int] = {}
        for method in ("unidade_medida", "description", "fallback"):
            total = 0
            for day in buckets:
                total += await self._get_int(f"stats:parsemethod:{method}:{day}")
            methods[method] = total
        out["parse_method_distribution"] = methods
        return out

    async def costs(self, days: int = 14) -> dict[str, Any]:
        buckets = _last_days(days)
        out: dict[str, Any] = {
            "days": buckets,
            "cost_usd": [],
            "calls": [],
            "input_tokens": [],
            "output_tokens": [],
        }
        for day in buckets:
            out["cost_usd"].append(round(await self._get_float(f"stats:llm:cost:{day}"), 6))
            out["calls"].append(await self._get_int(f"stats:llm:calls:{day}"))
            out["input_tokens"].append(await self._get_int(f"stats:llm:in_tok:{day}"))
            out["output_tokens"].append(await self._get_int(f"stats:llm:out_tok:{day}"))
        models_raw = await self._redis.smembers("stats:llm:models")
        per_model = []
        for model in sorted(self._dec(m) for m in models_raw):
            calls = in_tok = out_tok = 0
            cost = 0.0
            for day in buckets:
                rec = self._decode_map(
                    await self._redis.hgetall(f"stats:llm:model:{model}:{day}")
                )
                if not rec:
                    continue
                calls += int(rec.get("calls", 0) or 0)
                in_tok += int(rec.get("in_tok", 0) or 0)
                out_tok += int(rec.get("out_tok", 0) or 0)
                cost += float(rec.get("cost", 0) or 0)
            per_model.append(
                {
                    "model": model,
                    "calls": calls,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cost_usd": round(cost, 6),
                }
            )
        out["per_model"] = per_model
        return out

    async def recent_searches(self, limit: int = 50) -> list[dict[str, Any]]:
        try:
            entries = await self._redis.xrevrange("events:search", count=limit)
        except Exception:  # pragma: no cover
            return []
        return [self._stream_fields(eid, fields) for eid, fields in entries]

    async def items(self, days: int = 14, top: int = 20) -> dict[str, Any]:
        return {
            "top_searched": await self._merge_zsets("stats:items:searched", days, top),
            "top_not_found": await self._merge_zsets("stats:items:notfound", days, top),
        }

    async def feedback(self, limit: int = 50, kind: str | None = None) -> dict[str, Any]:
        try:
            entries = await self._redis.xrevrange("events:feedback", count=limit * 3)
        except Exception:  # pragma: no cover
            entries = []
        items = [self._stream_fields(eid, f) for eid, f in entries]
        if kind:
            items = [i for i in items if i.get("kind") == kind]
        items = items[:limit]
        counts = {
            k: await self._get_int(f"stats:feedback:{k}:total") for k in FEEDBACK_KINDS
        }
        return {"items": items, "counts": counts}

    async def timings(self, days: int = 14) -> dict[str, Any]:
        """Per-subsystem latency over the window + the full response-time
        distribution and daily trend (goals: user wait time + subsystem health)."""
        buckets = _last_days(days)
        stages = []
        distribution = [0] * _N_BUCKETS
        for stage in TIMING_STAGES:
            agg = await self._merge_hist(f"stats:timing:{stage}", buckets)
            summary = self._lat_summary(agg["count"], agg["sum_ms"], agg["buckets"])
            summary["stage"] = stage
            stages.append(summary)
            if stage == "total":
                distribution = agg["buckets"]
        series_avg: list[float] = []
        series_p95: list[float] = []
        series_count: list[int] = []
        for day in buckets:
            rec = self._decode_map(
                await self._redis.hgetall(f"stats:timing:total:{day}")
            )
            count = int(rec.get("count", 0) or 0)
            sum_ms = float(rec.get("sum_ms", 0) or 0)
            day_buckets = [int(rec.get(f"b{i}", 0) or 0) for i in range(_N_BUCKETS)]
            series_avg.append(round(sum_ms / count, 1) if count else 0.0)
            series_p95.append(_percentile_from_buckets(day_buckets, 0.95))
            series_count.append(count)
        return {
            "days": buckets,
            "buckets_ms": list(_LATENCY_BUCKETS_MS),
            "stages": stages,
            "distribution": distribution,
            "total_series": {
                "avg_ms": series_avg,
                "p95_ms": series_p95,
                "count": series_count,
            },
        }

    async def providers(self, days: int = 14) -> dict[str, Any]:
        """Latency + error rate per external provider over the window."""
        try:
            names = sorted(
                self._dec(p) for p in await self._redis.smembers("stats:providers")
            )
        except Exception:  # pragma: no cover
            names = []
        out = []
        buckets = _last_days(days)
        for name in names:
            agg = await self._merge_hist(f"stats:provider:{name}", buckets)
            summary = self._lat_summary(agg["count"], agg["sum_ms"], agg["buckets"])
            calls = agg["count"]
            errors = agg["errors"]
            tot = self._decode_map(
                await self._redis.hgetall(f"stats:provider:{name}:total")
            )
            out.append(
                {
                    "name": name,
                    "calls": calls,
                    "errors": errors,
                    "error_rate": self._rate(errors, calls),
                    "avg_ms": summary["avg_ms"],
                    "p50_ms": summary["p50_ms"],
                    "p95_ms": summary["p95_ms"],
                    "last_ok_ts": tot.get("last_ok_ts"),
                    "last_error_ts": tot.get("last_error_ts"),
                }
            )
        return {"providers": out}

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _stream_fields(entry_id: Any, fields: dict[Any, Any]) -> dict[str, Any]:
        def dec(v: Any) -> Any:
            return v.decode() if isinstance(v, bytes) else v

        out = {dec(k): dec(v) for k, v in fields.items()}
        out["id"] = dec(entry_id)
        return out

    async def _merge_hist(self, prefix: str, day_buckets: list[str]) -> dict[str, Any]:
        """Sum daily latency-histogram hashes (``stats:timing:*`` / ``stats:provider:*``)
        over a window. Handles both ``count`` (timings) and ``calls`` (providers)."""
        agg = {"count": 0, "sum_ms": 0.0, "errors": 0, "buckets": [0] * _N_BUCKETS}
        for day in day_buckets:
            try:
                rec = self._decode_map(await self._redis.hgetall(f"{prefix}:{day}"))
            except Exception:  # pragma: no cover
                rec = {}
            if not rec:
                continue
            agg["count"] += int(rec.get("count") or rec.get("calls") or 0)
            agg["sum_ms"] += float(rec.get("sum_ms") or 0)
            agg["errors"] += int(rec.get("errors") or 0)
            for i in range(_N_BUCKETS):
                agg["buckets"][i] += int(rec.get(f"b{i}") or 0)
        return agg

    @staticmethod
    def _lat_summary(count: int, sum_ms: float, buckets: list[int]) -> dict[str, Any]:
        return {
            "count": count,
            "avg_ms": round(sum_ms / count, 1) if count else 0.0,
            "p50_ms": _percentile_from_buckets(buckets, 0.5),
            "p95_ms": _percentile_from_buckets(buckets, 0.95),
        }

    async def _merge_zsets(
        self, prefix: str, days: int, top: int
    ) -> list[dict[str, Any]]:
        totals: dict[str, float] = {}
        for day in _last_days(days):
            try:
                rows = await self._redis.zrevrange(
                    f"{prefix}:{day}", 0, top - 1, withscores=True
                )
            except Exception:  # pragma: no cover
                rows = []
            for member, score in rows:
                m = member.decode() if isinstance(member, bytes) else member
                totals[m] = totals.get(m, 0.0) + float(score)
        ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top]
        return [{"label": label, "count": int(count)} for label, count in ranked]
