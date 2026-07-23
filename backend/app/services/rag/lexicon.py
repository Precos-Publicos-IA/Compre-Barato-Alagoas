"""Optional external match lexicon (Phase 5).

Loading is **opt-in** via ``MATCH_LEXICON_PATH`` (or ``load_match_lexicon``).
Default = no file → intent behaves exactly as hard-coded rules.

Safety:
- Miner output ships as ``heads`` + ``synonym_candidates`` only.
- ``synonym_candidates`` are **never** applied to production synonym expansion.
- Only explicitly reviewed ``promoted_synonym_groups`` (if present in the file)
  participate in ``expand_synonyms`` when the lexicon is loaded.
- Never auto-merge cross-head poison; promotion is a human/review step.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ENV_MATCH_LEXICON_PATH = "MATCH_LEXICON_PATH"

# Module state — empty by default (5-S4).
_loaded_path: str | None = None
_raw: dict[str, Any] | None = None
_known_heads: frozenset[str] = frozenset()
_brand_skips: frozenset[str] = frozenset()
_promoted_syn_groups: tuple[frozenset[str], ...] = ()


def lexicon_env_path() -> str | None:
    raw = (os.environ.get(ENV_MATCH_LEXICON_PATH) or "").strip()
    return raw or None


def is_lexicon_loaded() -> bool:
    return _raw is not None


def loaded_lexicon_path() -> str | None:
    return _loaded_path


def lexicon_known_heads() -> frozenset[str]:
    """Heads listed in the loaded lexicon (informational / hints)."""
    return _known_heads


def lexicon_brand_skips() -> frozenset[str]:
    """Optional brand-first skip tokens from lexicon (hints only)."""
    return _brand_skips


def lexicon_promoted_syn_groups() -> tuple[frozenset[str], ...]:
    """Reviewed synonym groups only — never raw miner candidates."""
    return _promoted_syn_groups


def lexicon_raw() -> dict[str, Any] | None:
    return _raw


def clear_match_lexicon() -> None:
    """Unload lexicon (tests / default restore)."""
    global _loaded_path, _raw, _known_heads, _brand_skips, _promoted_syn_groups
    _loaded_path = None
    _raw = None
    _known_heads = frozenset()
    _brand_skips = frozenset()
    _promoted_syn_groups = ()


def _parse_heads(data: dict[str, Any]) -> frozenset[str]:
    heads = data.get("heads") or []
    out: set[str] = set()
    for h in heads:
        if isinstance(h, str) and h.strip():
            out.add(h.strip().lower())
        elif isinstance(h, dict):
            tok = (h.get("token") or h.get("head") or "").strip().lower()
            if tok:
                out.add(tok)
    return frozenset(out)


def _parse_brand_skips(data: dict[str, Any]) -> frozenset[str]:
    raw = data.get("brand_skip_hints") or data.get("brand_skips") or []
    out: set[str] = set()
    for b in raw:
        if isinstance(b, str) and b.strip():
            out.add(b.strip().lower())
        elif isinstance(b, dict):
            tok = (b.get("token") or "").strip().lower()
            if tok:
                out.add(tok)
    return frozenset(out)


def _parse_promoted_groups(data: dict[str, Any]) -> tuple[frozenset[str], ...]:
    """Only ``promoted_synonym_groups`` — never synonym_candidates."""
    groups = data.get("promoted_synonym_groups") or []
    out: list[frozenset[str]] = []
    for g in groups:
        if isinstance(g, (list, tuple, set, frozenset)):
            toks = {str(t).strip().lower() for t in g if str(t).strip()}
            if len(toks) >= 2:
                out.append(frozenset(toks))
        elif isinstance(g, dict):
            members = g.get("members") or g.get("tokens") or g.get("group") or []
            toks = {str(t).strip().lower() for t in members if str(t).strip()}
            if len(toks) >= 2:
                out.append(frozenset(toks))
    return tuple(out)


def load_match_lexicon(path: str | Path, *, strict: bool = False) -> dict[str, Any]:
    """Load a versioned lexicon JSON. Does not apply synonym_candidates."""
    global _loaded_path, _raw, _known_heads, _brand_skips, _promoted_syn_groups
    p = Path(path)
    if not p.is_file():
        msg = f"match lexicon not found: {p}"
        if strict:
            raise FileNotFoundError(msg)
        logger.warning(msg)
        clear_match_lexicon()
        return {}

    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"lexicon root must be object, got {type(data)}")

    _raw = data
    _loaded_path = str(p.resolve())
    _known_heads = _parse_heads(data)
    _brand_skips = _parse_brand_skips(data)
    _promoted_syn_groups = _parse_promoted_groups(data)
    logger.info(
        "loaded match lexicon path=%s heads=%d promoted_syn_groups=%d",
        _loaded_path,
        len(_known_heads),
        len(_promoted_syn_groups),
    )
    return data


def ensure_lexicon_from_env() -> bool:
    """If MATCH_LEXICON_PATH set and not yet loaded from that path, load it.

    Returns True when a lexicon is loaded after this call.
    """
    path = lexicon_env_path()
    if not path:
        return is_lexicon_loaded()
    if is_lexicon_loaded() and _loaded_path and Path(_loaded_path) == Path(path).resolve():
        return True
    if is_lexicon_loaded() and _loaded_path:
        # Path changed — reload
        clear_match_lexicon()
    load_match_lexicon(path, strict=False)
    return is_lexicon_loaded()


def maybe_autoload() -> None:
    """Idempotent: load from env if configured. Safe no-op when unset."""
    if lexicon_env_path():
        ensure_lexicon_from_env()


__all__ = [
    "ENV_MATCH_LEXICON_PATH",
    "clear_match_lexicon",
    "ensure_lexicon_from_env",
    "is_lexicon_loaded",
    "lexicon_brand_skips",
    "lexicon_env_path",
    "lexicon_known_heads",
    "lexicon_promoted_syn_groups",
    "lexicon_raw",
    "load_match_lexicon",
    "loaded_lexicon_path",
    "maybe_autoload",
]
