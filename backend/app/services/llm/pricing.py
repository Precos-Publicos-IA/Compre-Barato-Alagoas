"""Token pricing for LLM cost tracking.

Rates are USD per 1,000,000 tokens, taken from the public Anthropic pricing for the
models we might use. Cache reads/writes are priced relative to the input rate
(read ~0.1x, write ~1.25x). Matching is by model-id prefix so dated snapshots
(e.g. ``claude-haiku-4-5-20251001``) resolve to the same entry.

Source of truth: the Claude API pricing reference. Update here when rates change.
"""

from __future__ import annotations

# model-id prefix -> (input $/1M, output $/1M)
PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
}

_CACHE_READ_MULT = 0.1
_CACHE_WRITE_MULT = 1.25


def _rates(model: str) -> tuple[float, float]:
    for prefix, rate in PRICES.items():
        if model.startswith(prefix):
            return rate
    # Unknown model: fall back to Haiku rates so cost is never silently zero.
    return PRICES["claude-haiku-4-5"]


def cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """Estimated USD cost for one LLM call."""
    in_rate, out_rate = _rates(model)
    cost = (
        input_tokens * in_rate
        + output_tokens * out_rate
        + cache_read_tokens * in_rate * _CACHE_READ_MULT
        + cache_creation_tokens * in_rate * _CACHE_WRITE_MULT
    ) / 1_000_000
    return round(cost, 6)
