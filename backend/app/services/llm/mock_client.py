"""Deterministic, rule-based stand-in for the Claude list parser.

Good enough to run and test the full flow: it splits compound lines, extracts the
requested quantity (digits, fractions, and Brazilian phrasings like "meia dúzia" or
"um e meio"), strips trailing sizes, and drops Portuguese stopwords to produce a clean
SEFAZ search term while preserving a readable label.
"""

from __future__ import annotations

import re

from .base import LLMClient, ParsedItem, ParseResult

# Split compound lines on semicolons/newlines, the conjunction " e ", and a slash or
# comma that separates items ("arroz/feijão", "arroz, feijão"). We deliberately do NOT
# split on:
#   - " e " when it forms "X e meio" (one and a half),
#   - a slash inside a numeric fraction ("1/2"), or
#   - a comma inside a decimal ("1,5"),
# so the quantity parser below sees those tokens whole.
_SPLIT_RE = re.compile(
    r"[;\n]+|\s+e\s+(?!meio|1/2|½)|(?<!\d)/(?!\d)|(?<!\d),(?!\d)", re.IGNORECASE
)

# Size tokens to strip from the search term (the size is not the keyword).
_SIZE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:kg|kgs|g|gr|mg|l|lt|ml|cl|un|und|unid|dz|pct|cx|fardo|pacote|caixa)\b",
    re.IGNORECASE,
)
_MULTIPACK_RE = re.compile(r"\b\d+\s*[x×]\s*\d+\s*\w*\b", re.IGNORECASE)
_STOPWORDS = {"de", "da", "do", "das", "dos", "a", "o", "as", "os", "com", "sem"}
# Bare measurement words left over after the quantity is consumed ("um e meio kg arroz"
# -> "kg arroz"). They are units, not the product, so drop them from the search term.
_UNIT_WORDS = {
    "kg", "kgs", "g", "gr", "grama", "gramas", "l", "lt", "litro", "litros",
    "ml", "cl", "quilo", "quilos", "un", "und", "unid", "dz", "duzia", "dúzia",
    "pct", "pacote", "pacotes", "cx", "caixa", "caixas", "fardo", "fardos",
}

# Spelled-out small numbers people speak/type instead of digits.
_WORD_QTY = {
    "uma": 1, "um": 1, "dois": 2, "duas": 2, "tres": 3, "três": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
}


def _extract_requested_qty(text: str) -> tuple[str, int]:
    """Return ``(remaining_text, quantity)`` for one basket token.

    Handles the common ways our audience expresses "how many":
    digits ("3", "2x"), a dozen ("dúzia" -> 12, "meia dúzia" -> 6), one-and-a-half
    forms ("um e meio", "1 e meio", "1,5" -> 2), spelled numbers, and bare fractions
    ("1/2 kg" -> a single descriptive entry, qty 1).
    """
    t = text.strip()
    if not t:
        return t, 1

    # "meia dúzia" / "1/2 dúzia" / "½ dúzia" -> 6
    m = re.match(r"^\s*(?:meia[\s-]*d[úu]zia|1/2\s*d[úu]zia|½\s*d[úu]zia)\b", t, re.I)
    if m:
        return t[m.end():].strip(), 6

    # "dúzia" / "dz" used as a count -> 12
    m = re.match(r"^\s*(?:d[úu]zia|dz)\b", t, re.I)
    if m:
        return t[m.end():].strip(), 12

    # "um e meio" / "1 e meio" / "2 e meio" / "2 e 1/2" -> base + 1
    m = re.match(r"^\s*(?:um|uma|(\d+))\s*e\s*(?:meio|1/2|½)\b", t, re.I)
    if m:
        base = int(m.group(1)) if m.group(1) else 1
        return t[m.end():].strip(), base + 1

    # "1,5" / "1.5" decimal form of one-and-a-half -> 2
    m = re.match(r"^\s*1[.,]5\s*(?:x|un|und|kg|g|l|ml|d[úu]zia)?\s*", t, re.I)
    if m:
        return t[m.end():].strip(), 2

    # Bare numeric fraction prefix ("1/2 kg", "½ ") — the half is descriptive, qty 1.
    m = re.match(r"^\s*(?:\d+/\d+|½)\s*(?:x|un|und|kg|g|l|ml)?\s*", t, re.I)
    if m:
        return t[m.end():].strip(), 1

    # Spelled-out number leading the token ("dois arroz").
    m = re.match(r"^\s*([a-zà-ú]+)\b", t, re.I)
    if m and m.group(1).lower() in _WORD_QTY:
        return t[m.end():].strip(), _WORD_QTY[m.group(1).lower()]

    # Classic leading digit ("3", "2x", "4 un").
    m = re.match(r"^\s*(\d+)\s*(?:x|un|und|unid|pct|cx)?\s+", t, re.I)
    if m:
        return t[m.end():].strip(), max(1, int(m.group(1)))

    return t, 1


def _clean_term(token: str) -> tuple[str, int]:
    text, qty = _extract_requested_qty(token)
    text = _MULTIPACK_RE.sub(" ", text)
    text = _SIZE_RE.sub(" ", text)
    words = [
        w
        for w in re.split(r"\s+", text.strip())
        if w and w.lower() not in _STOPWORDS and w.lower() not in _UNIT_WORDS
    ]
    return " ".join(words).strip(), qty


class MockLLMClient(LLMClient):
    source_name = "mock"

    async def parse_list(self, raw_items: list[str]) -> ParseResult:
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
        # Mock parser does no real LLM call: usage=None signals "estimate cost".
        return ParseResult(items=out, usage=None)
