"""Deterministic, rule-based stand-in for the Claude list parser.

Good enough to run and test the full flow: it splits compound lines, strips leading
counts and trailing sizes, and drops Portuguese stopwords to produce a clean SEFAZ
search term while preserving a readable label.
"""

from __future__ import annotations

import re

from .base import LLMClient, ParsedItem

# Split on commas, semicolons, newlines, slashes and the conjunction " e ".
_SPLIT_RE = re.compile(r"[,;\n/]+|\s+e\s+", re.IGNORECASE)
# Leading count like "2", "2x", "3 un".
_LEADING_COUNT_RE = re.compile(r"^\s*(\d+)\s*(?:x|un|und|unid|pct|cx)?\s+", re.IGNORECASE)
# Size tokens to strip from the search term.
_SIZE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:kg|kgs|g|gr|mg|l|lt|ml|cl|un|und|unid|dz|pct|cx|fardo)\b",
    re.IGNORECASE,
)
_MULTIPACK_RE = re.compile(r"\b\d+\s*[x×]\s*\d+\s*\w*\b", re.IGNORECASE)
_STOPWORDS = {"de", "da", "do", "das", "dos", "a", "o", "as", "os", "com", "sem"}


def _clean_term(token: str) -> tuple[str, int]:
    text = token.strip()
    qty = 1
    m = _LEADING_COUNT_RE.match(text)
    if m:
        qty = max(1, int(m.group(1)))
        text = text[m.end():]
    text = _MULTIPACK_RE.sub(" ", text)
    text = _SIZE_RE.sub(" ", text)
    words = [w for w in re.split(r"\s+", text.strip()) if w and w.lower() not in _STOPWORDS]
    return " ".join(words).strip(), qty


class MockLLMClient(LLMClient):
    source_name = "mock"

    async def parse_list(self, raw_items: list[str]) -> list[ParsedItem]:
        out: list[ParsedItem] = []
        seen: set[str] = set()
        for raw in raw_items:
            for token in _SPLIT_RE.split(raw):
                token = token.strip()
                if not token:
                    continue
                term, qty = _clean_term(token)
                if not term:
                    term = token
                key = term.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    ParsedItem(
                        raw=token,
                        label=token,
                        search_term=term,
                        quantity=qty,
                    )
                )
        return out
