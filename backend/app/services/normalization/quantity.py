"""Extract package size / quantity from messy free-text product descriptions.

The SEFAZ feed has no structured size field, so we mine it from strings like::

    "LEITE NA CAIXA 1L"        -> 1 L
    "ARROZ TIPO1 5KG"          -> 5 kg
    "CAFE A VACUO 250G"        -> 0.25 kg (via to_base)
    "CERVEJA LATA 350ML C/12"  -> 12 x 350 ml  (multipack)
    "OVOS BRANCOS C/12"        -> 12 un
    "REFRIGERANTE 1,5 L"       -> 1.5 L

This deterministic pass is fast, free and handles the overwhelming majority of
descriptions. Ambiguous leftovers are escalated to the LLM matcher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .units import _UNIT_TABLE, normalize_unit_token, to_base

# Build a unit alternation, longest tokens first so "ml" wins over "l", "kg" over "g".
# "mg" is excluded on purpose: in groceries/medicine it's a dosage strength
# ("DIPIRONA 500MG"), never the package size we compare on — letting it through would
# turn a 10-pill box into a meaningless 0.005 kg comparison.
_UNIT_TOKENS = sorted((t for t in _UNIT_TABLE if t != "mg"), key=len, reverse=True)
_UNIT_ALT = "|".join(re.escape(t) for t in _UNIT_TOKENS)

# A number (comma or dot decimals) immediately followed by a unit token.
# - (?<![\w.,]) : the number must not be glued to a preceding word/number
# - (?![a-zà-ú]) : the unit must not be the prefix of a larger word ("1lata")
_SIZE_RE = re.compile(
    rf"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*({_UNIT_ALT})(?![a-zà-ú])",
    re.IGNORECASE,
)

# Multipack: "12x500ml", "6 X 1 L", "12X350ML".
_MULTIPACK_RE = re.compile(
    rf"(?<![\w.,])(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*({_UNIT_ALT})(?![a-zà-ú])",
    re.IGNORECASE,
)

# Pack count markers without a size: "C/12", "C/ 6", "CX12", "LEVE 6", "12UN".
_PACKCOUNT_RE = re.compile(
    r"(?:c/\s*|cx\s*|leve\s*|kit\s*|pack\s*)(\d+)\b",
    re.IGNORECASE,
)

_MASS_VOLUME = {"mass", "volume"}


@dataclass(frozen=True)
class ParsedQuantity:
    """A quantity extracted from a description.

    ``value``/``unit`` are in the raw (matched) unit. ``base_value``/``base_unit`` are
    the canonical form (kg / L / un). ``confidence`` is a rough 0..1 reliability score
    used to decide whether to trust the parse or escalate.
    """

    value: float
    unit: str
    base_value: float
    base_unit: str
    confidence: float
    multipack: bool
    source: str  # the substring we matched, for debugging/traceability


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def _dimension(unit: str) -> str | None:
    entry = _UNIT_TABLE.get(normalize_unit_token(unit))
    return entry[0] if entry else None


def extract_quantity(description: str) -> ParsedQuantity | None:
    """Best-effort extraction of a package size from a description.

    Returns None when nothing usable is found (the caller then treats the item as a
    single unit with ``quantity_parsed=False``).
    """
    if not description:
        return None
    text = description.strip()

    # 1) Multipack with explicit size, e.g. "12X500ML" -> 12 * 0.5 L.
    mp = _MULTIPACK_RE.search(text)
    if mp:
        count = int(mp.group(1))
        size = _to_float(mp.group(2))
        unit = mp.group(3)
        base = to_base(size * count, unit)
        if base:
            return ParsedQuantity(
                value=size * count,
                unit=normalize_unit_token(unit),
                base_value=base[0],
                base_unit=base[1],
                confidence=0.95,
                multipack=True,
                source=mp.group(0),
            )

    # 2) Simple sizes anywhere in the string.
    sizes = [
        (_to_float(m.group(1)), m.group(2), m.group(0))
        for m in _SIZE_RE.finditer(text)
    ]
    pack = _PACKCOUNT_RE.search(text)
    pack_count = int(pack.group(1)) if pack else None

    # Prefer a mass/volume size (that's what makes per-kg/L comparison meaningful).
    mv_sizes = [s for s in sizes if _dimension(s[1]) in _MASS_VOLUME]
    if mv_sizes:
        value, unit, src = mv_sizes[0]
        multipack = False
        # A pack count alongside a unit size implies a multipack (e.g. cans C/12).
        if pack_count and pack_count > 1:
            value *= pack_count
            multipack = True
        base = to_base(value, unit)
        if base:
            return ParsedQuantity(
                value=value,
                unit=normalize_unit_token(unit),
                base_value=base[0],
                base_unit=base[1],
                confidence=0.9 if not multipack else 0.85,
                multipack=multipack,
                source=src,
            )

    # 3) Count-only pack ("OVOS C/12", "DUZIA", "12 UN").
    if pack_count and pack_count > 1:
        base = to_base(pack_count, "un")
        assert base
        return ParsedQuantity(
            value=float(pack_count),
            unit="un",
            base_value=base[0],
            base_unit=base[1],
            confidence=0.75,
            multipack=True,
            source=pack.group(0),  # type: ignore[union-attr]
        )

    # 4) A bare count unit like "... 12UN" or "DUZIA".
    count_sizes = [s for s in sizes if _dimension(s[1]) == "count"]
    if count_sizes:
        value, unit, src = count_sizes[0]
        base = to_base(value, unit)
        if base and base[0] > 1:
            return ParsedQuantity(
                value=value,
                unit=normalize_unit_token(unit),
                base_value=base[0],
                base_unit=base[1],
                confidence=0.7,
                multipack=False,
                source=src,
            )

    return None
