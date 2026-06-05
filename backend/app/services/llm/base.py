"""LLM client interface for list parsing and ambiguous matching.

In v1 the real implementation calls Claude Haiku; the mock is a deterministic
rule-based parser so the app runs and is tested with no API key. Both honour the same
contract, so flipping ``USE_MOCK_LLM`` is the only change needed later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ParsedItem:
    """One concrete product the user wants, derived from a raw basket line."""

    raw: str           # the original text the user typed/said
    label: str         # human label to show back (cleaned)
    search_term: str   # the keyword sent to SEFAZ `descricao`
    quantity: int = 1  # how many they want (used for totals later; v1 keeps 1)


@runtime_checkable
class LLMClient(Protocol):
    source_name: str

    async def parse_list(self, raw_items: list[str]) -> list[ParsedItem]:
        """Split/normalize free-text basket lines into searchable items."""
        ...
