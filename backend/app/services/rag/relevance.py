"""Deterministic grocery relevance scoring (zero LLM cost).

Key idea: for staples, the product word must appear as a *primary* token near
the start of the NFC-e description. Containing "leite" inside a cookie name is
not a milk hit.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..normalization.matcher import NormalizedOffer

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)

# Leading/category noise (cookie, candy, pet, seasoning, hygiene, …).
_NOISE = re.compile(
    r"\b("
    r"bala|balas|pirulito|chiclete|chocolate|choc|bombom|caramel[oa]|confeito|"
    r"bisc(?:oito)?|bolacha|cookie|wafer|kitkat|snickers|trento|"
    r"bolao|bola\s*de\s*leite|fondant|amanteigado|maluquinho|"
    r"tempero|temp|sazon|caldo|tablete|maggi|sache|temperinho|condimento|"
    r"floc(?:ao|ão)?|farinha|crem[ea]|macarr[aã]o|snack|barra|granola|granofibra|"
    r"caes?|c[aã]o|gatos?|dog|cat|ra[cç][aã]o|pet|filhote|canina|felina|"
    r"animal(?:is)?|cachorro|arrozcao|amigaco|amigao|luppy|biluzao|"
    r"shampoo|sabonete|detergente|amaciante|desinfetante|"
    r"cigarro|cerveja|whisky|vodka|vinho|fermentado|ferm|iogurte|chamyto|"
    r"bebida|refresco|achocolatado|toddynho|pingo|"
    r"creme|cr\.?\s*leite|doce\s*de\s*leite|ferment|fermentado|chamyto|yakult|"
    r"coalhada|coal\b|bebida\s*lactea|l[aá]ctea"
    r")\b",
    re.I,
)

_PET_QUERY = re.compile(
    r"\b(c[aã]es?|c[aã]o|gato|dog|cat|ra[cç][aã]o|pet|cachorro)\b", re.I
)
_SWEET_QUERY = re.compile(
    r"\b(bala|chocolate|bombom|doce|cookie|biscoito)\b", re.I
)
_SEASONING_QUERY = re.compile(r"\b(tempero|sazon|caldo|maggi)\b", re.I)
_YOGURT_QUERY = re.compile(r"\b(iogurte|yakult|chamyto|fermentado)\b", re.I)

# Staple keys (accent-stripped) → positive package/type patterns.
_STAPLES = {
    "arroz": re.compile(
        r"\b(tipo\s*1|tp\s*1|t1|branco|parboil|parboilizado|integral|agulhinha|"
        r"[15]\s*kg|10\s*kg)\b",
        re.I,
    ),
    "leite": re.compile(
        r"\b(uht|integral|desnat|semi|zero\s*lact|longa\s*vida|em\s*po|"
        r"condensado|em\s*caixa|1\s*l|1000\s*ml)\b",
        re.I,
    ),
    "feijao": re.compile(
        r"\b(carioca|preto|mulatinho|fradinho|vermelho|tipo\s*1|[12]\s*kg)\b",
        re.I,
    ),
    "pao": re.compile(
        r"\b(frances|forma|integral|bisnaga|hot\s*dog|hamburguer|sortido)\b",
        re.I,
    ),
    "acucar": re.compile(r"\b(cristal|refinado|demerara|mascavo|[15]\s*kg)\b", re.I),
    "oleo": re.compile(r"\b(soja|girassol|milho|canola|900\s*ml|1\s*l)\b", re.I),
    "cafe": re.compile(r"\b(torrado|moido|soluvel|capsula|p[oó]|500\s*g)\b", re.I),
    "ovo": re.compile(r"\b(branco|vermelho|caipira|bandeja|dz|duzia|30\s*un)\b", re.I),
    "ovos": re.compile(r"\b(branco|vermelho|caipira|bandeja|dz|duzia|30\s*un)\b", re.I),
    "macarrao": re.compile(r"\b(espaguete|parafuso|penne|ninho|integral|500\s*g)\b", re.I),
}

_STOP = frozenset(
    "de da do das dos com para tipo und un pct pacote cx kg g l ml ao".split()
)


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def _norm(s: str) -> str:
    return _strip_accents(s or "").lower().strip()


def _token_list(text: str) -> list[str]:
    t = _norm(text)
    return [m.group(0) for m in _TOKEN_RE.finditer(t) if len(m.group(0)) >= 2]


def _token_set(text: str) -> set[str]:
    return {t for t in _token_list(text) if t not in _STOP}


def _intent_staples(intent: str) -> list[str]:
    t = _norm(intent)
    out = []
    for k in _STAPLES:
        if re.search(rf"\b{k}\b", t):
            out.append(k)
    # synonyms
    if "feijão" in (intent or "").lower() and "feijao" not in out:
        out.append("feijao")
    if re.search(r"\bp[aã]o\b", intent or "", re.I) and "pao" not in out:
        out.append("pao")
    return out


def _primary_index(tokens: list[str], word: str) -> int | None:
    for i, t in enumerate(tokens[:6]):
        if t == word or t.startswith(word) or word.startswith(t):
            return i
    return None


def _user_allows_noise(intent: str, desc: str) -> bool:
    if _PET_QUERY.search(intent) and re.search(
        r"\b(cao|caes|dog|gato|racao|pet)\b", desc, re.I
    ):
        return True
    if _SWEET_QUERY.search(intent) and re.search(
        r"\b(bala|choc|chocolate|doce|bisc)\b", desc, re.I
    ):
        return True
    if _SEASONING_QUERY.search(intent) and re.search(
        r"\b(temp|tempero|sazon|caldo)\b", desc, re.I
    ):
        return True
    if _YOGURT_QUERY.search(intent) and re.search(
        r"\b(iogurte|ferm|chamyto)\b", desc, re.I
    ):
        return True
    return False


@dataclass(frozen=True)
class RelevanceResult:
    score: float
    kept: list[NormalizedOffer]
    dropped: int


def score_description(user_label: str, search_term: str, description: str) -> float:
    """Score a free-text product description against user intent (0..1)."""
    intent = f"{user_label} {search_term}".strip()
    desc = description or ""
    if not intent or not desc:
        return 0.0

    intent_n = _norm(intent)
    desc_n = _norm(desc)
    intent_toks = _token_set(intent)
    desc_tokens = _token_list(desc)
    desc_toks = {t for t in desc_tokens if t not in _STOP}
    if not intent_toks or not desc_toks:
        return 0.0

    content = {t for t in intent_toks if not re.fullmatch(r"\d+[a-z]*", t)}
    if not content:
        content = intent_toks

    overlap = content & desc_toks
    if not overlap:
        return 0.0

    # Hard gate: noise categories (cookie/candy/pet/seasoning) unless asked.
    # No exceptions for "primary token" — "ARROZ P CAES" and "CARAMELO LEITE" must die.
    if _NOISE.search(desc_n) and not _user_allows_noise(intent_n, desc_n):
        return 0.04

    # Hard gate for staples: product word must be among the first tokens.
    staples = _intent_staples(intent_n)
    if staples:
        best_idx = None
        for st in staples:
            idx = _primary_index(desc_tokens, st)
            if idx is None:
                continue
            best_idx = idx if best_idx is None else min(best_idx, idx)
        if best_idx is None:
            return 0.05
        if best_idx > 2:
            # "kitkat ao leite" — leite is late
            return 0.08
        # Primary position quality
        base = 0.55 if best_idx == 0 else (0.42 if best_idx == 1 else 0.30)
    else:
        base = 0.35 * (len(overlap) / max(len(content), 1))

    # Positive package/type cues for known staples.
    for st in staples:
        pat = _STAPLES.get(st)
        if pat and pat.search(desc_n):
            base += 0.22
        # Extra: plain UHT / carton milk over specialty dairy.
        if st == "leite" and re.search(r"\buht\b", desc_n) and re.search(
            r"\b(1\s*l|1000\s*ml|integral|desnat)\b", desc_n
        ):
            base += 0.12

    # Token overlap refinement
    base += 0.15 * (len(overlap) / max(len(content), 1))

    # Prefer plausible grocery prices later in ranking; score stays semantic.
    return max(0.0, min(1.0, base))


def score_offer(user_label: str, search_term: str, offer: NormalizedOffer) -> float:
    return score_description(user_label, search_term, offer.description or "")


def filter_offers(
    user_label: str,
    search_term: str,
    offers: list[NormalizedOffer],
    *,
    min_score: float = 0.35,
    max_keep: int | None = None,
) -> RelevanceResult:
    if not offers:
        return RelevanceResult(score=0.0, kept=[], dropped=0)

    scored = [(score_offer(user_label, search_term, o), o) for o in offers]
    # Best relevance first; among equals, cheaper unit price.
    scored.sort(key=lambda x: (-x[0], x[1].unit_price, x[1].price))
    best = scored[0][0]
    kept = [o for s, o in scored if s >= min_score]
    if not kept:
        if best < 0.20:
            return RelevanceResult(score=best, kept=[], dropped=len(offers))
        kept = [o for s, o in scored if s >= max(0.20, best - 0.05)][:12]
    if max_keep is not None:
        kept = kept[:max_keep]
    return RelevanceResult(
        score=best, kept=kept, dropped=max(0, len(offers) - len(kept))
    )
