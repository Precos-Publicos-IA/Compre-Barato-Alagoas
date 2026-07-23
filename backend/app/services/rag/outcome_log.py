"""Privacy-safe search outcome log for the self-improving matching loop.

When ``MATCH_OUTCOME_LOG_PATH`` is set, appends one JSONL row per requested
basket item after a search completes. Unset path → no-op (default). Sampled by
``MATCH_OUTCOME_LOG_SAMPLE`` (0.0–1.0, default 1.0).

Never logs device tokens, Authorization headers, or SEFAZ AppTokens.
"""

from __future__ import annotations

import json
import logging
import os
import random
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .intent import MATCH_RULES_VERSION, alignment_verdict, extract_intent
from .relevance import score_description

logger = logging.getLogger(__name__)

# Env keys (also documented in repo-root ``.env.example``).
ENV_LOG_PATH = "MATCH_OUTCOME_LOG_PATH"
ENV_LOG_SAMPLE = "MATCH_OUTCOME_LOG_SAMPLE"

# Cap stored tops — never dump full store/SKU payloads.
_MAX_TOP = 3
_MAX_DESC_LEN = 160

# Keys that must never appear in a logged record (secrets / identifiers).
_FORBIDDEN_KEYS = frozenset(
    {
        "device_token",
        "authorization",
        "Authorization",
        "sefaz_app_token",
        "SEFAZ_APP_TOKEN",
        "app_token",
        "admin_token",
        "password",
        "secret",
        "cookie",
        "Cookie",
    }
)

_write_lock = threading.Lock()


def outcome_log_path() -> str | None:
    """Return configured JSONL path, or None when logging is disabled."""
    raw = (os.environ.get(ENV_LOG_PATH) or "").strip()
    return raw or None


def outcome_log_sample_rate() -> float:
    """Sample rate in [0.0, 1.0]. Invalid values fall back to 1.0."""
    raw = (os.environ.get(ENV_LOG_SAMPLE) or "1.0").strip()
    try:
        rate = float(raw)
    except ValueError:
        return 1.0
    if rate < 0.0:
        return 0.0
    if rate > 1.0:
        return 1.0
    return rate


def is_enabled() -> bool:
    return outcome_log_path() is not None


def should_sample(sample_rate: float | None = None) -> bool:
    """Decide once per search whether to log (Bernoulli sample)."""
    rate = outcome_log_sample_rate() if sample_rate is None else sample_rate
    if rate <= 0.0:
        return False
    if rate >= 1.0:
        return True
    return random.random() < rate


def _truncate_desc(text: str | None) -> str:
    s = (text or "").strip()
    if len(s) <= _MAX_DESC_LEN:
        return s
    return s[: _MAX_DESC_LEN - 1] + "…"


def _sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Drop forbidden keys and any nested values that look like secrets."""
    out: dict[str, Any] = {}
    for k, v in record.items():
        if k in _FORBIDDEN_KEYS:
            continue
        kl = str(k).lower()
        if "token" in kl or "authorization" in kl or "password" in kl:
            continue
        out[k] = v
    return out


def build_item_outcome(
    *,
    query: str,
    search_term: str | None = None,
    top_descriptions: Sequence[str] | None = None,
    top_scores: Sequence[float] | None = None,
    items_fetch_failed: bool = False,
    stores_found: int = 0,
    data_source: str | None = None,
    latency_ms: float | None = None,
    list_id: str | None = None,
    analytics_id: str | None = None,
    request_id: str | None = None,
    match_rules_version: str | None = None,
    auto_label: str = "unknown",
    ts: str | None = None,
) -> dict[str, Any]:
    """Build one privacy-safe outcome dict (no I/O)."""
    q = (query or "").strip()
    st = (search_term or q).strip()
    intent = extract_intent(q)
    descs = [_truncate_desc(d) for d in (top_descriptions or []) if d][:_MAX_TOP]
    scores: list[float] = []
    if top_scores:
        for s in list(top_scores)[:_MAX_TOP]:
            try:
                scores.append(round(float(s), 4))
            except (TypeError, ValueError):
                continue
    # If scores missing, recompute from descriptions when possible.
    if not scores and descs:
        scores = [
            round(score_description(q, st, d), 4) for d in descs
        ]

    align = "unknown"
    if items_fetch_failed:
        align = "unknown"
    elif not descs:
        align = "unknown"
    else:
        align = alignment_verdict(q, descs[0])

    record: dict[str, Any] = {
        "ts": ts or datetime.now(timezone.utc).isoformat(),
        "request_id": request_id or uuid.uuid4().hex,
        "match_rules_version": match_rules_version or MATCH_RULES_VERSION,
        "query": q,
        "intent_head": intent.head or None,
        "intent_mods": sorted(intent.modifiers) if intent.modifiers else [],
        "search_term": st,
        "data_source": data_source,
        "items_fetch_failed": bool(items_fetch_failed),
        "latency_ms": int(latency_ms) if latency_ms is not None else None,
        "top_descriptions": descs,
        "top_scores": scores,
        "alignment_top": align,
        "auto_label": auto_label or "unknown",
        "stores_found": int(stores_found),
    }
    if list_id:
        record["list_id"] = list_id
    # Optional hashed client id only — never raw device_token.
    if analytics_id:
        record["analytics_id"] = analytics_id
    return _sanitize_record(record)


def append_outcome(
    record: Mapping[str, Any],
    *,
    path: str | None = None,
) -> bool:
    """Append one JSON line. Returns True if written.

    No-op when path is unset (and no override). Never raises to callers — logging
    failures are swallowed after a warning so search stays available.
    """
    target = (path if path is not None else outcome_log_path())
    if not target:
        return False
    safe = _sanitize_record(dict(record))
    # Defense in depth: refuse rows that still carry forbidden material.
    blob = json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    lower = blob.lower()
    for bad in ("device_token", "authorization:", "sefaz_app_token", "bearer "):
        if bad in lower:
            logger.warning("outcome_log: refused row with forbidden content")
            return False
    try:
        p = Path(target)
        if p.parent and str(p.parent) not in ("", "."):
            p.parent.mkdir(parents=True, exist_ok=True)
        line = blob + "\n"
        with _write_lock:
            with p.open("a", encoding="utf-8") as fh:
                fh.write(line)
        return True
    except OSError as exc:
        logger.warning("outcome_log: write failed path=%s err=%s", target, exc)
        return False


def log_search_item_outcomes(
    *,
    items: Sequence[Mapping[str, Any]] | Sequence[Any],
    offers_by_item: Mapping[str, Sequence[Any]] | None = None,
    stores_found: int = 0,
    data_source: str | None = None,
    fetch_failed_labels: Iterable[str] | None = None,
    latency_ms: float | None = None,
    list_id: str | None = None,
    analytics_id: str | None = None,
    request_id: str | None = None,
    path: str | None = None,
    sample_rate: float | None = None,
    force: bool = False,
) -> int:
    """Append one outcome row per requested item when enabled + sampled.

    ``items`` entries may be:
    - ``ParsedItem``-like objects with ``.label`` / ``.search_term``
    - dicts with ``label``/``query`` and optional ``search_term``
    - plain strings (query == search_term)

    Returns number of lines written. Safe no-op when path unset or sample misses.
    """
    target = path if path is not None else outcome_log_path()
    if not target and not force:
        return 0
    if not force and not should_sample(sample_rate):
        return 0

    failed = {str(x).strip().lower() for x in (fetch_failed_labels or []) if x}
    rid = request_id or uuid.uuid4().hex
    offers = offers_by_item or {}
    written = 0

    for raw in items:
        query, search_term = _item_query_term(raw)
        if not query:
            continue
        label_key = query  # offers keyed by label in search_service
        # Prefer exact key; fall back to case-insensitive match.
        item_offers = list(offers.get(label_key) or offers.get(query) or [])
        if not item_offers:
            for k, v in offers.items():
                if str(k).strip().lower() == query.lower():
                    item_offers = list(v or [])
                    break

        descs: list[str] = []
        scores: list[float] = []
        seen: set[str] = set()
        for o in item_offers:
            desc = getattr(o, "description", None)
            if desc is None and isinstance(o, Mapping):
                desc = o.get("description")
            d = _truncate_desc(str(desc) if desc else "")
            if not d or d.lower() in seen:
                continue
            seen.add(d.lower())
            descs.append(d)
            scores.append(round(score_description(query, search_term, d), 4))
            if len(descs) >= _MAX_TOP:
                break

        is_failed = query.strip().lower() in failed
        record = build_item_outcome(
            query=query,
            search_term=search_term,
            top_descriptions=descs,
            top_scores=scores,
            items_fetch_failed=is_failed,
            stores_found=stores_found,
            data_source=data_source,
            latency_ms=latency_ms,
            list_id=list_id,
            analytics_id=analytics_id,
            request_id=rid,
        )
        if append_outcome(record, path=target):
            written += 1
    return written


def _item_query_term(raw: Any) -> tuple[str, str]:
    if raw is None:
        return "", ""
    if isinstance(raw, str):
        q = raw.strip()
        return q, q
    if isinstance(raw, Mapping):
        q = str(raw.get("query") or raw.get("label") or raw.get("raw") or "").strip()
        st = str(raw.get("search_term") or q).strip()
        return q, st
    q = str(
        getattr(raw, "label", None)
        or getattr(raw, "raw", None)
        or getattr(raw, "query", None)
        or ""
    ).strip()
    st = str(getattr(raw, "search_term", None) or q).strip()
    return q, st


__all__ = [
    "ENV_LOG_PATH",
    "ENV_LOG_SAMPLE",
    "MATCH_RULES_VERSION",
    "append_outcome",
    "build_item_outcome",
    "is_enabled",
    "log_search_item_outcomes",
    "outcome_log_path",
    "outcome_log_sample_rate",
    "should_sample",
]
