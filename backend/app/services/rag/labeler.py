"""Cheap structural auto-labels for search outcomes (Phase 2).

Pure functions only — no I/O, no Redis, no LLM. Used by the outcome log,
offline rescore, learn policy, and eval reports.

Label set (fixed):
  good | weak | bad | empty_fetch | empty_no_data | unknown

Priority (must match docs/self-improving-matching-plan.md §2.1):
  1. items_fetch_failed          → empty_fetch
  2. no stores / no descriptions → empty_no_data
  3. alignment_verdict == reject → bad
  4. score < 0.2 (hard-reject floor) → bad
  5. score ≥ 0.5 and alignment ok and not noise → good
  6. mid score or known weak patterns → weak
  7. else → unknown
"""

from __future__ import annotations

import re
from typing import Literal

from .intent import alignment_verdict, norm_text
from .relevance import score_description

Label = Literal["good", "weak", "bad", "empty_fetch", "empty_no_data", "unknown"]

LABELS: frozenset[str] = frozenset(
    {"good", "weak", "bad", "empty_fetch", "empty_no_data", "unknown"}
)

# Match relevance hard-reject floor and "kept" threshold band.
BAD_SCORE_FLOOR = 0.2
GOOD_SCORE = 0.5

# Prepared-food / snack noise tops that are weak even with partial token overlap
# when the user did not ask for soup/sauce/snack.
_WEAK_TOP_NOISE = re.compile(
    r"\b("
    r"sopa|vono|"
    r"salg(?:adinho|ad|a)?|chips?|"
    r"molho|"
    r"tempero|caldo|sazon|maggi|"
    r"pastel|risoto|pizza|bolo|torta|"
    r"biscoito|bolacha|cookie"
    r")\b",
    re.I,
)
_USER_WANTS_NOISE = re.compile(
    r"\b("
    r"sopa|molho|salg(?:adinho)?|chips?|tempero|caldo|sazon|"
    r"pastel|risoto|pizza|bolo|torta|biscoito|bolacha|cookie"
    r")\b",
    re.I,
)


def _is_weak_noise_top(query: str, description: str) -> bool:
    """True when top desc is a prepared-food/noise carrier and user did not ask for it."""
    q = norm_text(query)
    d = norm_text(description)
    if not q or not d:
        return False
    if _USER_WANTS_NOISE.search(q):
        return False
    return bool(_WEAK_TOP_NOISE.search(d))


def auto_label(
    query: str,
    description: str | None,
    *,
    fetch_failed: bool = False,
    score: float | None = None,
    stores_found: int | None = None,
    search_term: str | None = None,
) -> Label:
    """Return a cheap structural label for one (query, top description) pair.

    Pure: no I/O. ``score`` may be omitted; when description is non-empty it is
    recomputed via ``score_description`` so callers (outcome log, offline
    rescore) stay consistent with the live scorer.

    ``stores_found`` is optional; when provided and ≤0 with no usable top
    description, the row is ``empty_no_data`` (match track had nothing to grade).
    """
    # 1) Fetch track failure is never a match label.
    if fetch_failed:
        return "empty_fetch"

    desc = (description or "").strip()
    no_desc = not desc
    no_stores = stores_found is not None and int(stores_found) <= 0

    # 2) Nothing to grade on the match track.
    if no_desc or no_stores:
        return "empty_no_data"

    q = (query or "").strip()
    term = (search_term or q).strip() or q

    # Resolve score (prefer caller-provided live score).
    resolved: float
    if score is None:
        resolved = float(score_description(q, term, desc)) if q else 0.0
    else:
        try:
            resolved = float(score)
        except (TypeError, ValueError):
            resolved = float(score_description(q, term, desc)) if q else 0.0

    # 3) Head alignment hard reject → bad (modifier pollution, class flip, …).
    align = alignment_verdict(q, desc) if q else "unknown"
    if align == "reject":
        return "bad"

    # 4) Hard-reject score floor (relevance returns ~0.04 for class rejects).
    if resolved < BAD_SCORE_FLOOR:
        return "bad"

    # Optional weak-noise heuristic before good (plan §2.1 step 6 patterns).
    # Applied when alignment is not a clear ok, or score is only mid-high.
    weak_noise = _is_weak_noise_top(q, desc)

    # 5) Strong match: score ≥ 0.5, alignment ok, not noise top.
    if resolved >= GOOD_SCORE and align == "ok" and not weak_noise:
        return "good"

    # 6) Mid band or known weak tops.
    if weak_noise:
        return "weak"
    if BAD_SCORE_FLOOR <= resolved < GOOD_SCORE:
        return "weak"
    # High score but alignment only "unknown" (cannot hard-claim good).
    if resolved >= GOOD_SCORE and align == "unknown":
        return "weak"

    # 7) Fallback.
    return "unknown"


def label_for_outcome(
    *,
    query: str,
    top_description: str | None,
    top_score: float | None,
    items_fetch_failed: bool,
    stores_found: int = 0,
    search_term: str | None = None,
) -> Label:
    """Convenience wrapper for outcome-log / batch callers."""
    return auto_label(
        query,
        top_description,
        fetch_failed=items_fetch_failed,
        score=top_score,
        stores_found=stores_found,
        search_term=search_term,
    )


__all__ = [
    "BAD_SCORE_FLOOR",
    "GOOD_SCORE",
    "LABELS",
    "Label",
    "auto_label",
    "label_for_outcome",
]
