"""Unit canonicalization for fair price comparison.

The SEFAZ API never returns a structured package size — only a free-text description
and a ``unidadeMedida`` (the *selling* unit). To compare prices fairly we reduce every
measurement to one of three canonical base units:

* mass   -> ``kg``
* volume -> ``L``
* count  -> ``un``

``to_base`` converts a (value, unit) pair into the canonical base; ``dimension`` tells
which of the three families a raw unit string belongs to.
"""

from __future__ import annotations

# Canonical base unit per dimension.
BASE_UNIT = {"mass": "kg", "volume": "L", "count": "un"}

# Maps a raw (lower-cased) unit token to (dimension, factor-to-base).
# Factor converts ONE of the raw unit into the canonical base unit.
_UNIT_TABLE: dict[str, tuple[str, float]] = {
    # --- mass -> kg ---
    "kg": ("mass", 1.0),
    "kgs": ("mass", 1.0),
    "quilo": ("mass", 1.0),
    "quilos": ("mass", 1.0),
    "k": ("mass", 1.0),
    "g": ("mass", 0.001),
    "gr": ("mass", 0.001),
    "grs": ("mass", 0.001),
    "grama": ("mass", 0.001),
    "gramas": ("mass", 0.001),
    "mg": ("mass", 1e-6),
    # --- volume -> L ---
    "l": ("volume", 1.0),
    "lt": ("volume", 1.0),
    "lts": ("volume", 1.0),
    "litro": ("volume", 1.0),
    "litros": ("volume", 1.0),
    "ml": ("volume", 0.001),
    "cl": ("volume", 0.01),
    # --- count -> un ---
    "un": ("count", 1.0),
    "und": ("count", 1.0),
    "unid": ("count", 1.0),
    "unidade": ("count", 1.0),
    "unidades": ("count", 1.0),
    "u": ("count", 1.0),
    "pc": ("count", 1.0),
    "pç": ("count", 1.0),
    "pct": ("count", 1.0),
    "pcte": ("count", 1.0),
    "pacote": ("count", 1.0),
    "cx": ("count", 1.0),
    "caixa": ("count", 1.0),
    "fd": ("count", 1.0),
    "fardo": ("count", 1.0),
    "dz": ("count", 12.0),
    "duzia": ("count", 12.0),
    "dúzia": ("count", 12.0),
    "par": ("count", 2.0),
}


def normalize_unit_token(unit: str) -> str:
    """Lower-case and strip punctuation/whitespace from a raw unit string."""
    return unit.strip().lower().rstrip(".")


def dimension(unit: str) -> str | None:
    """Return 'mass' | 'volume' | 'count' for a raw unit, or None if unknown."""
    entry = _UNIT_TABLE.get(normalize_unit_token(unit))
    return entry[0] if entry else None


def to_base(value: float, unit: str) -> tuple[float, str] | None:
    """Convert (value, unit) to (base_value, base_unit).

    Returns None when the unit is not recognised.
    """
    entry = _UNIT_TABLE.get(normalize_unit_token(unit))
    if entry is None:
        return None
    dim, factor = entry
    return value * factor, BASE_UNIT[dim]


def is_known_unit(unit: str) -> bool:
    return normalize_unit_token(unit) in _UNIT_TABLE
