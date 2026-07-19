"""Prompt-injection guardrails for user-supplied text sent to any LLM.

The catalog/training subsystem sends two kinds of externally-controlled text to
Claude:

- User-requested product names (free text from the ``/catalog/products/request``
  endpoint), which the daily training job asks the capable model to evaluate.
- SEFAZ NFC-e descriptions (business-authored, still untrusted), which the cheap
  model sees during output validation.

Neither is trustworthy. This module normalises that text into inert data before
it is embedded in a prompt (OWASP LLM01). It is the first layer; the system
prompts (which tell the model to treat the payload as data, never instructions)
are the second, and the JSON-only parsing + try/except fallbacks are the third.

``sanitize_for_llm`` never raises and always returns a short, single-line,
control-char-free string. ``looks_like_injection`` is a cheap heuristic used only
for logging/metrics — we sanitize regardless of what it returns.
"""

from __future__ import annotations

import re

# Phrases (PT-BR + EN) that are strong signals of an injection attempt. Matched
# case-insensitively; used both to null-out the phrase and to flag for logging.
_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|above|prior|earlier)\s+(?:instructions?|promp(?:t|ts))",
    r"ignore\s+(?:as\s+|todas\s+as\s+)?instru[cç][õo]es\s+(?:anteriores|acima)",
    r"disregard\s+(?:the\s+)?(?:previous|above)",
    r"desconsider[ae]\s+(?:as\s+)?instru[cç][õo]es",
    r"you\s+are\s+now\b",
    r"voc[eê]\s+agora\s+[eé]\b",
    r"act\s+as\b",
    r"aja\s+como\b",
    r"system\s*prompt",
    r"reveal|mostre|revele|repeat\s+(?:the\s+)?(?:above|prompt)",
    r"</?(?:system|user|assistant|instructions?)>",
    r"\[/?(?:INST|SYS|SYSTEM)\]",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# Delimiters an attacker could use to break out of the prompt's data fence:
# backticks (code fences) and the Unicode line/paragraph separators (U+2028/9).
_FENCE_RE = re.compile("[`  ]")
_WS_RE = re.compile(r"\s+")


def looks_like_injection(text: str | None) -> bool:
    """Cheap heuristic: does the text contain a known injection marker?

    For logging/metrics only. We always sanitize; a False here is not a
    guarantee of safety.
    """
    if not text:
        return False
    return bool(_INJECTION_RE.search(text))


def sanitize_for_llm(text: str | None, *, max_len: int = 120) -> str:
    """Return a prompt-safe, single-line version of untrusted ``text``.

    Steps (all defensive, never raises):
    1. Drop control characters (drop everything below 0x20 and DEL).
    2. Remove code fences / Unicode line separators that could break the
       surrounding prompt structure.
    3. Null out known injection phrases so a hijack line loses its verb.
    4. Collapse all whitespace to single spaces (kills multi-line payloads).
    5. Truncate to ``max_len`` so a payload can't blow the token budget.
    """
    if not text:
        return ""
    # 1. control chars -> space (so newline-joined words don't fuse together)
    cleaned = "".join(c if (ord(c) >= 32 and ord(c) != 127) else " " for c in text)
    # 2. fences / unicode line separators
    cleaned = _FENCE_RE.sub(" ", cleaned)
    # 3. neutralise injection phrases
    cleaned = _INJECTION_RE.sub(" ", cleaned)
    # 4. collapse whitespace
    cleaned = _WS_RE.sub(" ", cleaned).strip()
    # 5. length cap
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip()
    return cleaned
