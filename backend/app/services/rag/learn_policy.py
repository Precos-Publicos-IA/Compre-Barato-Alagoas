"""Central gate for all RAG mutations (Phase 3 learn_policy v2).

Production success/miss/feedback paths must go through this module — not
call ``RAGStore.record_success`` / ``record_miss`` directly (store primitives
remain for tests, prewarm seeding, and this policy).

Safety rails (plan §3.2–3.4):
- never success-learn on fetch_failed / empty
- never success-learn head-incompatible rewrites
- never success-learn alignment reject / weak score / package-class fail
- wrong_item demotes and never success-learns
- ``MATCH_LEARN=0`` makes all writes a no-op
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal

from .intent import alignment_verdict, rewrite_heads_compatible
from .store import RAGStore, rewrite_compatible

logger = logging.getLogger(__name__)

ENV_MATCH_LEARN = "MATCH_LEARN"
DEFAULT_MIN_SCORE_TO_LEARN = 0.50

LearnAction = Literal[
    "success",
    "miss",
    "demote",
    "noop",
    "refused_fetch_failed",
    "refused_empty",
    "refused_heads",
    "refused_alignment",
    "refused_score",
    "refused_package_class",
    "refused_disabled",
]


@dataclass(frozen=True)
class LearnResult:
    """Outcome of a learn-policy decision (for metrics / tests)."""

    action: LearnAction
    reason: str = ""


def learning_enabled() -> bool:
    """True unless ``MATCH_LEARN`` is explicitly off (0/false/no/off)."""
    raw = (os.environ.get(ENV_MATCH_LEARN) or "1").strip().lower()
    return raw not in ("0", "false", "no", "off", "")


def _alignment_ok_for_learn(
    user_term: str,
    best_description: str | None,
    score: float | None,
    min_score: float,
) -> tuple[bool, str]:
    """Accept when alignment is ok, or score≥τ and not reject (plan §3.2)."""
    desc = (best_description or "").strip()
    if not desc:
        # No description to grade: allow only if score already meets τ
        # (verifier path with kept offers should always pass a desc when possible).
        if score is not None and float(score) >= min_score:
            return True, "no_desc_score_ok"
        return False, "no_description"

    verdict = alignment_verdict(user_term, desc)
    if verdict == "reject":
        return False, "alignment_reject"
    if verdict == "ok":
        return True, "alignment_ok"
    # unknown: allow when score ≥ τ (not reject)
    if score is not None and float(score) >= min_score:
        return True, "alignment_unknown_score_ok"
    return False, "alignment_unknown_weak_score"


async def on_search_item_result(
    rag: RAGStore | None,
    *,
    user_term: str,
    effective_search_term: str,
    offers_found: int = 0,
    fetch_failed: bool = False,
    score: float | None = None,
    best_description: str | None = None,
    package_class_ok: bool | None = None,
    min_score_to_learn: float = DEFAULT_MIN_SCORE_TO_LEARN,
) -> LearnResult:
    """Gate positive/negative learn from one verified search item result.

    Positive learn only if **all** hold (plan §3.2):
    - learning enabled
    - not fetch_failed
    - at least one kept offer
    - rewrite_heads_compatible(user, search_term)
    - alignment ok (or score≥τ and not reject)
    - score ≥ min_score_to_learn
    - package_class_ok is not False (when already enforced by caller)

    Zero kept offers (and not fetch_failed) → soft ``record_miss``.
    """
    if not learning_enabled():
        return LearnResult("refused_disabled", "MATCH_LEARN off")

    if rag is None:
        return LearnResult("noop", "no_rag")

    u = (user_term or "").strip()
    e = (effective_search_term or "").strip()
    if not u or not e:
        return LearnResult("noop", "missing_terms")

    if fetch_failed:
        logger.debug("learn_policy: skip fetch_failed %r -> %r", u, e)
        return LearnResult("refused_fetch_failed", "items_fetch_failed")

    kept = int(offers_found or 0)

    # Miss path: nothing kept — soft signal, never success.
    if kept < 1:
        await rag.record_miss(user_term=u, attempted_search_term=e)
        return LearnResult("miss", "no_kept_offers")

    # --- Positive learn gates ---
    if not rewrite_heads_compatible(u, e):
        logger.info("learn_policy: refuse heads-incompatible %r -> %r", u, e)
        return LearnResult("refused_heads", "rewrite_heads_compatible=false")

    # Belt: residual class rules (store also re-checks on write).
    if not rewrite_compatible(u, e):
        logger.info("learn_policy: refuse rewrite_compatible %r -> %r", u, e)
        return LearnResult("refused_heads", "rewrite_compatible=false")

    if score is None or float(score) < float(min_score_to_learn):
        return LearnResult(
            "refused_score",
            f"score={score} < min_score_to_learn={min_score_to_learn}",
        )

    ok_align, align_reason = _alignment_ok_for_learn(
        u, best_description, score, float(min_score_to_learn)
    )
    if not ok_align:
        return LearnResult("refused_alignment", align_reason)

    if package_class_ok is False:
        return LearnResult("refused_package_class", "package_class_ok=false")

    await rag.record_success(
        user_term=u,
        effective_search_term=e,
        offers_found=kept,
    )
    return LearnResult("success", "learned")


async def on_user_feedback(
    rag: RAGStore | None,
    *,
    kind: str,
    query: str,
    description: str | None = None,
    effective_search_term: str | None = None,
    list_id: str | None = None,
) -> LearnResult:
    """Apply user feedback to RAG (plan §3.3).

    ``wrong_item`` with a query demotes the effective mapping(s) and records a
    miss — **never** success.

    When ``effective_search_term`` is set, only that rewrite is removed.
    Otherwise every learned rewrite for ``query`` is removed (API often only
    sends the user item label). ``description`` is logged for ops, not written
    as a success mapping.
    """
    del list_id  # reserved for future outcome correlation

    if not learning_enabled():
        return LearnResult("refused_disabled", "MATCH_LEARN off")

    if rag is None:
        return LearnResult("noop", "no_rag")

    k = (kind or "").strip().lower()
    q = (query or "").strip()
    if not q:
        return LearnResult("noop", "missing_query")

    if k == "wrong_item":
        eff = (effective_search_term or "").strip()
        if eff:
            targets = [eff]
        else:
            # API path often has only the user label — clear all known rewrites.
            known = await rag.lookup_effective_terms(q, limit=20)
            # Also clear any raw zset members (including pre-filter poison rows).
            try:
                from .store import _norm  # same keying as RAGStore writes

                raw = await rag.redis.zrevrange(f"rag:effective_for:{_norm(q)}", 0, 19)
                for r in raw or []:
                    term = r.decode() if isinstance(r, (bytes, bytearray)) else str(r)
                    if term and term not in known:
                        known.append(term)
            except Exception:  # pragma: no cover
                logger.debug("wrong_item raw zset scan failed", exc_info=True)
            targets = known or [q]

        for t in targets:
            await rag.record_miss(user_term=q, attempted_search_term=t)
            await rag.demote(user_term=q, effective_search_term=t, remove=True)

        logger.info(
            "learn_policy: wrong_item demote query=%r targets=%r desc=%r",
            q,
            targets,
            (description or "")[:80],
        )
        return LearnResult("demote", "wrong_item")

    # helpful / other: no RAG mutation from feedback alone
    return LearnResult("noop", f"kind={k}")


__all__ = [
    "DEFAULT_MIN_SCORE_TO_LEARN",
    "ENV_MATCH_LEARN",
    "LearnAction",
    "LearnResult",
    "learning_enabled",
    "on_search_item_result",
    "on_user_feedback",
]
