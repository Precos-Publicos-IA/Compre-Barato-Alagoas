"""LLM client interface for list parsing and ambiguous matching.

In v1 the real implementation calls Claude Haiku; the mock is a deterministic
rule-based parser so the app runs and is tested with no API key. Both honour the same
contract, so flipping ``USE_MOCK_LLM`` is the only change needed later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ParsedItem:
    """One concrete product the user wants, derived from a raw basket line."""

    raw: str           # the original text the user typed/said
    label: str         # human label to show back (cleaned)
    search_term: str   # the keyword sent to SEFAZ `descricao`
    quantity: int = 1  # how many they want (used for totals later; v1 keeps 1)


@dataclass(frozen=True)
class LLMUsage:
    """Token usage for one LLM call — feeds cost tracking on the dashboard.

    ``None`` from a client means "no real call" (mock parser, or the real client
    fell back after an error); the caller estimates tokens in that case.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


@dataclass(frozen=True)
class ParseResult:
    """The parsed basket plus the token usage of the call that produced it."""

    items: list[ParsedItem] = field(default_factory=list)
    usage: LLMUsage | None = None


@runtime_checkable
class LLMClient(Protocol):
    source_name: str

    async def parse_list(self, raw_items: list[str]) -> ParseResult:
        """Split/normalize free-text basket lines into searchable items."""
        ...
