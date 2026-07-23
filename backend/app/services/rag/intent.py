"""Head-aligned product intent (systemic matching spine).

Portuguese NFC-e and shopping queries are free text. Token *overlap* is not
product identity: ``queijo`` is not ``pão de queijo``, ``frango`` is not
``pastel de frango``.

This module extracts a structural ``ProductIntent`` (head + modifiers) and
decides head compatibility. Callers must treat ``reject`` as a hard gate —
no per-SKU denylist required for the modifier-pollution class of failures.

Design rules (stable, product-agnostic):
1. ``X de Y`` → head=X, Y is a modifier (flavor/ingredient/cut carrier).
2. Single token → that token is the head.
3. Sequence ``X Y…`` → head=X, remaining content are soft modifiers.
4. User head only matching a *modifier* under a different head → reject.
5. Synonym / small hypernym groups only (category-level), never SKU pairs.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)

# Function words kept for ``X de Y`` parsing; stripped from content sets.
_STOP = frozenset(
    "de da do das dos com para em no na nos nas um uma uns umas ao a o e ou "
    "tipo und un pct pacote cx kg g l ml lt po em c".split()
)

# Connectors that create "head de modifier" compounds in grocery Portuguese.
_DE_CONN = frozenset({"de", "do", "da", "dos", "das"})
_COM_CONN = frozenset({"com", "c"})

# Trailing pack / unit noise — never product heads.
_SIZE_OR_UNIT = frozenset(
    {
        "kg",
        "g",
        "mg",
        "ml",
        "l",
        "lt",
        "lts",
        "un",
        "und",
        "unidade",
        "unidades",
        "pct",
        "pc",
        "pacote",
        "pacotes",
        "cx",
        "caixa",
        "fd",
        "fardo",
        "dz",
        "duzia",
        "duzias",
        "bandeja",
        "tipo",
        "tp",
        "t1",
        "t2",
        "po",
        "uht",
    }
)

# Synonym groups (accent-stripped). Category-level only.
_SYN_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"ovo", "ovos"}),
    frozenset({"pao", "paes"}),
    frozenset({"cafe", "cafes"}),
    frozenset({"feijao", "feijoes"}),
    frozenset({"oleo", "oleos"}),
    frozenset({"acucar", "acucares"}),
    frozenset({"maca", "macas"}),
    frozenset({"limao", "limoes"}),
    frozenset({"sabao", "saboes"}),
    frozenset({"queijo", "queijos"}),
)

# Soft hypernyms: specific form → broader grocery head (still small + stable).
# Used only for heads_compatible, not for inventing SEFAZ terms.
_HYPERNYM_TO_PARENT: dict[str, str] = {
    "mussarela": "queijo",
    "muzarela": "queijo",
    "muçarela": "queijo",
    "prato": "queijo",
    "coalho": "queijo",
    "minas": "queijo",
    "provolone": "queijo",
    "parmesao": "queijo",
    "cheddar": "queijo",
    "ricota": "queijo",
    "gorgonzola": "queijo",
}

AlignmentVerdict = Literal["reject", "ok", "unknown"]


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def norm_text(text: str) -> str:
    return _strip_accents(text or "").lower().strip()


def token_list(text: str) -> list[str]:
    t = norm_text(text)
    return [m.group(0) for m in _TOKEN_RE.finditer(t) if len(m.group(0)) >= 2]


def expand_synonyms(toks: set[str]) -> set[str]:
    out = set(toks)
    for group in _SYN_GROUPS:
        if out & group:
            out |= group
    # Hypernym: child implies parent (mussarela → queijo), not the reverse alone.
    for child, parent in _HYPERNYM_TO_PARENT.items():
        if child in out:
            out.add(parent)
    return out


def _is_size_token(tok: str) -> bool:
    if tok in _SIZE_OR_UNIT:
        return True
    if re.fullmatch(r"\d+[a-z]*", tok):
        return True
    if re.fullmatch(r"\d+", tok):
        return True
    return False


def _is_head_candidate(tok: str) -> bool:
    if not tok or tok in _STOP or _is_size_token(tok):
        return False
    # Tiny abbreviations (cf, s, r) are not grocery heads.
    if len(tok) < 3:
        return False
    return True


def token_matches(a: str, b: str) -> bool:
    """Strict-ish stem match: ovo↔ovos, never sal⊂salsicha."""
    if not a or not b:
        return False
    if a == b:
        return True
    if a == b + "s" or b == a + "s":
        return True
    if a == b + "es" or b == a + "es":
        return True
    # Prefix only for longer stems (avoid 3-letter false friends).
    if len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True
    return False


def heads_compatible(head_a: str, head_b: str) -> bool:
    if not head_a or not head_b:
        return False
    ea = expand_synonyms({head_a})
    eb = expand_synonyms({head_b})
    if ea & eb:
        return True
    for a in ea:
        for b in eb:
            if token_matches(a, b):
                return True
    return False


def _content_tokens_ordered(raw_tokens: list[str]) -> list[str]:
    return [t for t in raw_tokens if t not in _STOP and not _is_size_token(t)]


@dataclass(frozen=True)
class ProductIntent:
    """Structural read of a query or NFC-e description."""

    head: str
    modifiers: frozenset[str]
    required: frozenset[str]
    all_content: frozenset[str]
    structure: str  # "single" | "x_de_y" | "sequence" | "empty"
    raw: str

    def expanded_content(self) -> set[str]:
        return expand_synonyms(set(self.all_content))

    def expanded_modifiers(self) -> set[str]:
        return expand_synonyms(set(self.modifiers))

    def expanded_required(self) -> set[str]:
        return expand_synonyms(set(self.required))


def extract_intent(text: str) -> ProductIntent:
    """Extract product head + modifiers from free text (query or description)."""
    raw = (text or "").strip()
    tokens = token_list(raw)
    if not tokens:
        return ProductIntent(
            head="",
            modifiers=frozenset(),
            required=frozenset(),
            all_content=frozenset(),
            structure="empty",
            raw=raw,
        )

    # Walk tokens with connectors preserved to find first X de/do/da Y.
    structure = "sequence"
    head = ""
    modifiers: list[str] = []
    required: list[str] = []

    i = 0
    n = len(tokens)
    # Skip leading size-only junk
    while i < n and not _is_head_candidate(tokens[i]) and tokens[i] not in _DE_CONN:
        i += 1

    if i >= n:
        content = _content_tokens_ordered(tokens)
        h = content[0] if content else ""
        rest = content[1:] if len(content) > 1 else []
        return ProductIntent(
            head=h,
            modifiers=frozenset(rest),
            required=frozenset(),
            all_content=frozenset(content),
            structure="single" if len(content) <= 1 else "sequence",
            raw=raw,
        )

    # Find X <de|do|da|com> Y with X,Y head candidates.
    found_de = False
    j = i
    while j < n - 2:
        left = tokens[j]
        mid = tokens[j + 1]
        right = tokens[j + 2]
        if (
            _is_head_candidate(left)
            and mid in _DE_CONN | _COM_CONN
            and _is_head_candidate(right)
        ):
            head = left
            structure = "x_de_y"
            required = [right]
            modifiers = [right]
            # Further content after the compound
            k = j + 3
            while k < n:
                if _is_head_candidate(tokens[k]):
                    modifiers.append(tokens[k])
                k += 1
            found_de = True
            break
        j += 1

    if not found_de:
        content = _content_tokens_ordered(tokens)
        if not content:
            return ProductIntent(
                head="",
                modifiers=frozenset(),
                required=frozenset(),
                all_content=frozenset(),
                structure="empty",
                raw=raw,
            )
        head = content[0]
        modifiers = content[1:]
        structure = "single" if len(content) == 1 else "sequence"
        # Sequence modifiers are soft for scoring (feijão preto ≈ FEIJAO PT).
        # Rewrite safety uses disjoint-modifier checks instead of hard required.
        required = []

    content_set = set(_content_tokens_ordered(tokens))
    if head:
        content_set.add(head)
    content_set.update(modifiers)

    return ProductIntent(
        head=head,
        modifiers=frozenset(modifiers),
        required=frozenset(required),
        all_content=frozenset(content_set),
        structure=structure,
        raw=raw,
    )


def _find_content_index(content: list[str], word: str) -> int | None:
    expanded = expand_synonyms({word})
    for i, t in enumerate(content):
        te = expand_synonyms({t})
        if te & expanded:
            return i
        for a in expanded:
            if token_matches(t, a):
                return i
    return None


def _required_satisfied(user: ProductIntent, desc: ProductIntent, desc_content: list[str]) -> bool:
    if not user.required:
        return True
    desc_pool = expand_synonyms(set(desc_content) | set(desc.all_content))
    for r in user.required:
        rexp = expand_synonyms({r})
        if desc_pool & rexp:
            continue
        if any(token_matches(r, t) or token_matches(t, r) for t in desc_pool):
            continue
        return False
    return True


def alignment_verdict(user_label: str, description: str) -> AlignmentVerdict:
    """Structural head alignment between user intent and an NFC-e line.

    * ``reject`` — clear head mismatch / modifier pollution (hard fail).
    * ``ok`` — heads align or user head is early primary product token.
    * ``unknown`` — cannot decide; caller may fall through to soft scoring.
    """
    u = extract_intent(user_label)
    d = extract_intent(description)
    if not u.head or u.structure == "empty":
        return "unknown"
    if not d.head and d.structure == "empty":
        return "reject"

    desc_content = _content_tokens_ordered(token_list(description))
    u_heads = expand_synonyms({u.head})
    d_heads = expand_synonyms({d.head}) if d.head else set()
    d_mods = d.expanded_modifiers()

    # --- 1) Modifier pollution (the forever fix for pão-de-X / pastel-de-X) ---
    # Description is "HEAD de MOD…"; user asked for MOD alone (or synonym), not HEAD.
    if d.structure == "x_de_y" and d.head:
        user_is_mod = bool(u_heads & d_mods) or any(
            token_matches(u.head, m) for m in d.modifiers
        )
        user_asks_desc_head = heads_compatible(u.head, d.head) or bool(
            expand_synonyms(set(u.all_content)) & d_heads
        )
        if user_is_mod and not user_asks_desc_head:
            return "reject"

    # --- 2) Direct head compatibility ---
    if d.head and heads_compatible(u.head, d.head):
        if not _required_satisfied(u, d, desc_content):
            return "reject"
        return "ok"

    # --- 3) User head appears as early primary product token (brand-first lines) ---
    idx = _find_content_index(desc_content, u.head)
    if idx is not None and idx <= 2:
        # Still reject if we're clearly under a different X-de-Y head.
        if d.structure == "x_de_y" and d.head and not heads_compatible(u.head, d.head):
            if u_heads & d_mods:
                return "reject"
        if not _required_satisfied(u, d, desc_content):
            return "reject"
        return "ok"

    # --- 4) User head absent from description entirely ---
    if idx is None:
        # Shared tokens only via unrelated leftovers → reject when we have signal
        shared = expand_synonyms(set(u.all_content)) & expand_synonyms(
            set(d.all_content) | set(desc_content)
        )
        # Hypernym-only share (mussarela line vs queijo query) handled if heads align;
        # if head absent and no head match, reject soft overlaps.
        if shared and not (u_heads & expand_synonyms(set(desc_content))):
            # Exception: hypernym child in description for parent query
            for t in desc_content:
                if heads_compatible(u.head, t):
                    if _required_satisfied(u, d, desc_content):
                        return "ok"
            return "reject"
        if not shared:
            return "reject"
        return "unknown"

    # User head only late in the string (secondary mention) → reject
    if idx is not None and idx > 2:
        return "reject"

    return "unknown"


def rewrite_heads_compatible(user_term: str, effective: str) -> bool:
    """Whether ``effective`` is a safe search rewrite for ``user_term`` by heads."""
    u = extract_intent(user_term)
    e = extract_intent(effective)
    if not u.head or not e.head:
        return False
    if not heads_compatible(u.head, e.head):
        return False
    # Must not drop required X-de-Y modifiers (peito de frango ↛ peito only / frango only).
    if u.required:
        e_pool = e.expanded_content()
        for r in u.required:
            rexp = expand_synonyms({r})
            if not (e_pool & rexp) and not any(
                token_matches(r, t) for t in e_pool
            ):
                return False
    # Different specializations under the same head (papel higiênico ≠ papel toalha).
    u_extra = expand_synonyms(set(u.all_content)) - expand_synonyms({u.head})
    e_extra = expand_synonyms(set(e.all_content)) - expand_synonyms({e.head})
    if u_extra and e_extra and not (u_extra & e_extra):
        # Both sides specialized with disjoint modifiers → unsafe rewrite
        return False
    return True
