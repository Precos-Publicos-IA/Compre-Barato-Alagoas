"""Canonical staple terms for Redis/RAG prewarm and post-deploy SEFAZ cache warm.

Kept in the app package so deploy scripts and unit tests share one list.
Do not invent product prices here — only search terms users type.
"""

from __future__ import annotations

# (user term, effective SEFAZ search_term, RAG weight)
# Weights seed the rewrite zset so first organic success is not fighting empty RAG.
STAPLE_RAG_MAPPINGS: list[tuple[str, str, int]] = [
    # Grains / staples
    ("arroz", "arroz tipo 1", 30),
    ("arroz", "arroz branco", 20),
    ("feijao", "feijao carioca", 25),
    ("feijão", "feijao carioca", 25),
    ("feijao preto", "feijao preto", 12),
    ("feijão preto", "feijao preto", 12),
    ("acucar", "acucar cristal", 12),
    ("açúcar", "acucar cristal", 12),
    ("sal", "sal refinado", 10),
    ("farinha de trigo", "farinha de trigo", 10),
    ("farinha de mandioca", "farinha de mandioca", 8),
    ("fuba", "fuba", 6),
    ("fubá", "fuba", 6),
    ("macarrao", "macarrao espaguete", 10),
    ("macarrão", "macarrao espaguete", 10),
    ("aveia", "aveia", 6),
    # Dairy / protein
    ("leite", "leite uht", 30),
    ("leite", "leite integral", 15),
    ("leite integral", "leite integral", 12),
    ("leite desnatado", "leite desnatado", 8),
    ("leite em po", "leite em po", 8),
    ("leite em pó", "leite em po", 8),
    ("ovos", "ovos", 12),
    ("ovo", "ovos", 12),
    ("manteiga", "manteiga", 8),
    ("margarina", "margarina", 6),
    ("queijo", "queijo mussarela", 10),
    ("queijo mussarela", "queijo mussarela", 8),
    ("requeijao", "requeijao", 6),
    ("requeijão", "requeijao", 6),
    ("iogurte", "iogurte natural", 6),
    # Oils / pantry
    ("oleo", "oleo de soja", 12),
    ("óleo", "oleo de soja", 12),
    ("oleo de soja", "oleo de soja", 10),
    ("óleo de soja", "oleo de soja", 10),
    ("azeite", "azeite", 6),
    ("vinagre", "vinagre", 5),
    ("molho de tomate", "molho de tomate", 8),
    ("cafe", "cafe torrado", 12),
    ("café", "cafe torrado", 12),
    ("cafe soluvel", "cafe soluvel", 6),
    ("café solúvel", "cafe soluvel", 6),
    # Bread
    ("pao", "pao frances", 20),
    ("pão", "pao frances", 20),
    ("pao de forma", "pao de forma", 8),
    ("pão de forma", "pao de forma", 8),
    ("pao frances", "pao frances", 10),
    ("pão francês", "pao frances", 10),
    # Produce / protein (high-frequency basket)
    ("frango", "frango", 8),
    ("peito de frango", "peito de frango", 8),
    ("carne moida", "carne moida", 6),
    ("carne moída", "carne moida", 6),
    ("banana", "banana prata", 6),
    ("tomate", "tomate", 6),
    ("batata", "batata", 6),
    ("cebola", "cebola", 5),
    ("alho", "alho", 5),
    # Cleaning / hygiene (often missing under load — still worth warm attempt)
    ("sabao", "sabao em po", 8),
    ("sabão", "sabao em po", 8),
    ("sabao em po", "sabao em po", 8),
    ("sabão em pó", "sabao em po", 8),
    ("detergente", "detergente", 6),
    ("papel higienico", "papel higienico", 6),
    ("papel higiênico", "papel higienico", 6),
    ("sabonete", "sabonete", 5),
    ("shampoo", "shampoo", 5),
    ("creme dental", "creme dental", 5),
]


# Terms sent to POST /api/v1/search to fill sefaz:search:* (non-empty only).
# Order = warm priority. Keep modest length so post-deploy prewarm finishes
# without stampeding SEFAZ (batched + delayed in the prewarm script).
STAPLE_FETCH_TERMS: list[str] = [
    "arroz",
    "feijao",
    "leite",
    "acucar",
    "oleo",
    "pao",
    "cafe",
    "ovos",
    "macarrao",
    "manteiga",
    "sal",
    "farinha de trigo",
    "molho de tomate",
    "frango",
    "queijo",
    "banana",
    "tomate",
    "detergente",
    "sabao em po",
    "papel higienico",
]


def unique_fetch_terms(terms: list[str] | None = None) -> list[str]:
    """Dedupe fetch terms case-insensitively, preserve first-seen order."""
    src = terms if terms is not None else STAPLE_FETCH_TERMS
    seen: set[str] = set()
    out: list[str] = []
    for t in src:
        key = t.strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(t.strip())
    return out


def _strip_accents(s: str) -> str:
    import unicodedata

    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def _fold_term(s: str) -> str:
    """casefold + strip accents for staple map keys."""
    return _strip_accents(s.strip()).casefold()


def staple_effective_term(user_term: str) -> str | None:
    """Best static SEFAZ rewrite for a user staple label (no Redis required).

    Used as cold-start fallback when RAG zsets are empty so prewarm of
    ``feijao`` / ``ovos`` still helps accented or singular user queries after
    the requester rewrites them to the shared effective term.
    """
    if not user_term or not str(user_term).strip():
        return None
    # Lazy map: folded user label -> (weight, effective)
    global _STAPLE_EFFECTIVE_BY_USER  # noqa: PLW0603 — module cache
    if _STAPLE_EFFECTIVE_BY_USER is None:
        m: dict[str, tuple[int, str]] = {}
        for user, effective, weight in STAPLE_RAG_MAPPINGS:
            k = _fold_term(user)
            prev = m.get(k)
            if prev is None or weight > prev[0]:
                m[k] = (weight, effective)
        _STAPLE_EFFECTIVE_BY_USER = m
    hit = _STAPLE_EFFECTIVE_BY_USER.get(_fold_term(user_term))
    return hit[1] if hit else None


_STAPLE_EFFECTIVE_BY_USER: dict[str, tuple[int, str]] | None = None


CORE_STAPLE_FETCH_SET = frozenset(
    {
        "arroz",
        "feijao",
        "feijão",
        "leite",
        "acucar",
        "açúcar",
        "oleo",
        "óleo",
        "pao",
        "pão",
        "cafe",
        "café",
        "ovos",
        "ovo",
    }
)
