"""Shared SEFAZ query/product text normalization (#279).

Mock and live HTTP clients should apply the same accent/case/whitespace pass so
local QA does not diverge from production keyword behaviour for pt-BR input.
"""

from __future__ import annotations

import re
import unicodedata

_WS_RE = re.compile(r"\s+")


def normalize_sefaz_text(text: str) -> str:
    """NFKD, strip combining marks, casefold, collapse internal whitespace, trim."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return _WS_RE.sub(" ", stripped.casefold()).strip()


# Back-compat alias used by older mock code paths / tests.
strip_accents = normalize_sefaz_text
