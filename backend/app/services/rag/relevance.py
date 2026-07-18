"""Deterministic grocery relevance scoring (zero LLM cost).

Key idea: for staples, the product word must appear as a *primary* token near
the start of the NFC-e description. Containing "leite" inside a cookie name is
not a milk hit.

PR1 (search quality): package-class priors for staples, hard rejects for
off-intent oil (coco/tiny) and pasta-as-egg (MAC/MACARR), so ranking cannot
crown sachets or macarrão "c/ovos" as the shopping answer.

PR2 / match-eval-100 P0: stop egg cross-bleed for non-egg queries; reject
sal-as-snack, óleo saturado / fish-in-oil, tempero-para-feijão, zero-açúcar
candy, and café caramel/spice mixes.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..normalization.matcher import NormalizedOffer
from ..normalization.quantity import extract_quantity

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)

# Leading/category noise (cookie, candy, pet, seasoning, hygiene, …).
# Note: MAC/MACARR abbreviations are handled in egg-specific pasta noise (not
# global — "MAC" alone can appear in other brands).
_NOISE = re.compile(
    r"\b("
    r"bala|balas|pirulito|chiclete|chocolate|choc|bombom|caramel[oa]s?|confeito|"
    r"bisc(?:oito)?|bolacha|cookie|wafer|kitkat|snickers|trento|"
    r"bolao|bola\s*de\s*leite|fondant|amanteigado|maluquinho|bigbig|"
    r"tempero|tempeiro|tempe|temp|sazon|caldo|tablete|maggi|sache|temperinho|condimento|"
    r"floc(?:ao|ão)?|farinha|crem[ea]|macarr[aã]o|snack|barra|granola|granofibra|"
    r"caes?|c[aã]o|gatos?|dog|cat|ra[cç][aã]o|pet|filhote|canina|felina|"
    r"animal(?:is)?|cachorro|arrozcao|amigaco|amigao|luppy|biluzao|"
    r"shampoo|sabonete|detergente|amaciante|desinfetante|"
    r"cigarro|cerveja|whisky|vodka|vinho|fermentado|ferm|iogurte|chamyto|"
    r"bebida|refresco|achocolatado|toddynho|pingo|"
    r"creme|cr\.?\s*leite|doce\s*de\s*leite|ferment|fermentado|chamyto|yakult|"
    r"coalhada|coalh|coal\b|bebida\s*lactea|l[aá]ctea"
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

# Pasta signals when user wants eggs (W1.2 / W1.3).
_PASTA_FULL = re.compile(
    r"\b("
    r"macarr[aã]o|espaguete|parafuso|penne|ninho|nissin|lamen|l[aá]men|"
    r"miojo|talharim|parafusinho|padrezinho|massa\s+com"
    r")\b",
    re.I,
)
_PASTA_ABBREV = frozenset({"mac", "macarr"})

# Coconut oil off-intent for plain "óleo" (W1.3).
_COCO = re.compile(r"\bcoco\b", re.I)
_COOKING_OIL_TYPES = re.compile(
    r"\b(soja|girassol|milho|canola|composto|algod[aã]o|oliva)\b", re.I
)
# Non-cooking / off-intent oil labels (match-eval-100: OLEO SATURADO, sardinha).
_OIL_OFF_INTENT = re.compile(
    r"\b("
    r"saturado|saturada|"
    r"sard(?:inha|\.)?|atum|conserva|"
    r"mist(?:ura|\.)?|"
    r"em\s+oleo|c/\s*oleo"
    r")\b",
    re.I,
)
# Table-salt positive cues vs snack "sal" flavor.
_SALT_PRODUCT = re.compile(
    r"\b(refinado|grosso|light|iodado|marinho|rosa|himalaia|cisne|"
    r"1\s*kg|500\s*g|1kg)\b",
    re.I,
)
_SALT_SNACK = re.compile(
    r"\b("
    r"pipoca|castanha|salg(?:adinho|ad|a)?|chips?|batata|amendoim|"
    r"milho|torrada|croc|snack|s\s*sal|sem\s*sal|c/\s*sal|ceb\s*sal"
    r")\b",
    re.I,
)
# Seasoning-for-beans (not the beans themselves).
_BEAN_SEASONING = re.compile(
    r"\b(tempero|tempeiro|tempe|temp|sazon|caldo|maggi|temperinho|condimento)\b",
    re.I,
)
# Zero-sugar candy / confection marketed with "açúcar".
_SUGAR_CANDY = re.compile(
    r"\b("
    r"zero\s*acucar|sem\s*acucar|0\s*acucar|"
    r"bigbig|bala|balas|chiclete|pirulito|bombom|confeito|"
    r"faca\s*a\s*festa|festa|sch\b|sache"
    r")\b",
    re.I,
)
# Coffee impostors: caramels and multi-spice blends (not 3 Corações brand alone).
_COFFEE_JUNK = re.compile(
    r"\b(caramel[oa]s?|bala|balas|chiclete|bombom)\b",
    re.I,
)
_COFFEE_SPICE_MIX = re.compile(
    r"\b(canela|cravo|gengibre|pimenta|cominho)\b",
    re.I,
)
_COFFEE_PRODUCT = re.compile(
    r"\b(torrado|moido|mo[ií]do|soluvel|sol[uú]vel|capsula|c[aá]psula|"
    r"pilao|pil[aã]o|extraforte|tradicional|gourmet|grao|gr[aã]o|"
    r"500\s*g|250\s*g|1\s*kg)\b",
    re.I,
)
# Egg product detection for cross-query bleed (non-egg intents).
_EGG_TOKEN = re.compile(r"\bovos?\b", re.I)

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
    "oleo": re.compile(
        r"\b(soja|girassol|milho|canola|composto|900\s*ml|500\s*ml|1\s*l)\b", re.I
    ),
    "cafe": re.compile(r"\b(torrado|moido|soluvel|capsula|p[oó]|500\s*g)\b", re.I),
    "sal": re.compile(
        r"\b(refinado|grosso|light|iodado|marinho|rosa|1\s*kg|500\s*g)\b", re.I
    ),
    "ovo": re.compile(
        r"\b(branco|vermelho|caipira|bandeja|dz|duzia|d[uú]zia|"
        r"[0-9]+\s*un|c/\s*[0-9]+)\b",
        re.I,
    ),
    "ovos": re.compile(
        r"\b(branco|vermelho|caipira|bandeja|dz|duzia|d[uú]zia|"
        r"[0-9]+\s*un|c/\s*[0-9]+)\b",
        re.I,
    ),
    "macarrao": re.compile(r"\b(espaguete|parafuso|penne|ninho|integral|500\s*g)\b", re.I),
}

_STOP = frozenset(
    "de da do das dos com para tipo und un pct pacote cx kg g l ml ao".split()
)

# Package-class ranks (lower is better for ranking). Used by ranking + learn guard.
# 0 = preferred grocery pack; 1 = acceptable; 2 = demoted (single egg, odd size);
# 3 = outlier / tiny (should usually already be filtered).
_CLASS_PREFERRED = 0
_CLASS_OK = 1
_CLASS_DEMOT = 2
_CLASS_OUTLIER = 3
_CLASS_UNKNOWN = 1

# Cooking oil: reject below this volume (L). 50 ml sachets are not "óleo" shopping.
_OIL_MIN_L = 0.05
# Preferred cooking oil pack: ~500 ml – 1.2 L.
_OIL_PREF_LO = 0.45
_OIL_PREF_HI = 1.2
# Sugar preferred around 1–5 kg.
_SUGAR_PREF_LO = 0.8
_SUGAR_PREF_HI = 5.5
# Eggs: bandeja/dúzia class is 6+.
_EGG_PREF_MIN = 6


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


def _expand_synonyms(toks: set[str]) -> set[str]:
    """ovo/ovos (and similar) must match each other for staple scoring."""
    out = set(toks)
    if "ovo" in out or "ovos" in out:
        out.update({"ovo", "ovos"})
    return out


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
    # bare "açúcar" accent form
    if re.search(r"\ba[cç][uú]car\b", intent or "", re.I) and "acucar" not in out:
        out.append("acucar")
    if re.search(r"\b[oó]leo\b", intent or "", re.I) and "oleo" not in out:
        out.append("oleo")
    if re.search(r"\bcaf[eé]\b", intent or "", re.I) and "cafe" not in out:
        out.append("cafe")
    return out


def _token_matches_word(token: str, word: str) -> bool:
    """Strict-ish token match: avoid sal⊂salg, but keep ovo⊂ovos / feijao⊂feijoes."""
    if token == word:
        return True
    # Simple plural (pt-BR-ish): ovo/ovos, cafe/cafes
    if token == word + "s" or word == token + "s":
        return True
    if token == word + "es" or word == token + "es":
        return True
    # Longer stems only: "macarrao" vs "macarr" handled elsewhere; never let
    # 3-letter query words prefix-match snacks (sal → salg).
    if len(word) >= 4 and len(token) >= 4:
        if token.startswith(word) or word.startswith(token):
            return True
    return False


def _primary_index(tokens: list[str], word: str) -> int | None:
    for i, t in enumerate(tokens[:6]):
        if _token_matches_word(t, word):
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
    # User asked for pasta → allow macarrão noise tokens.
    if re.search(r"\bmacarr", intent, re.I) and re.search(
        r"\b(mac|macarr|macarrao|espaguete)\b", desc, re.I
    ):
        return True
    # User asked for flour → allow "farinha" product lines (noise for other staples).
    if re.search(r"\bfarinha\b", intent, re.I) and re.search(
        r"\bfarinha\b", desc, re.I
    ):
        return True
    # User asked for cereal bars → allow barra.
    if re.search(r"\bbarra\b", intent, re.I) and re.search(r"\bbarra\b", desc, re.I):
        return True
    return False


def _is_egg_intent(intent_n: str) -> bool:
    return bool(re.search(r"\bovos?\b", intent_n))


def _is_oil_intent(intent_n: str) -> bool:
    return bool(re.search(r"\boleo\b", intent_n))


def _is_sugar_intent(intent_n: str) -> bool:
    return bool(re.search(r"\bacucar\b", intent_n))


def _is_salt_intent(intent_n: str) -> bool:
    # Plain "sal" or "sal refinado" — not "salgadinho" / "salsicha".
    return bool(re.search(r"\bsal\b", intent_n)) and not bool(
        re.search(r"\b(salgadinho|salsicha|salame)\b", intent_n)
    )


def _is_bean_intent(intent_n: str) -> bool:
    return bool(re.search(r"\bfeijao\b", intent_n))


def _is_coffee_intent(intent_n: str) -> bool:
    return bool(re.search(r"\bcafe\b", intent_n))


def _query_wants_coco(intent_n: str) -> bool:
    return bool(_COCO.search(intent_n))


def _is_pasta_as_egg_noise(desc_n: str, desc_tokens: list[str]) -> bool:
    """MAC / MACARR / macarrão / nissin … as egg impostors (W1.2)."""
    if _PASTA_FULL.search(desc_n):
        return True
    # Abbreviation as an early product token (e.g. "MAC OVOS FURADINHO").
    for t in desc_tokens[:4]:
        if t in _PASTA_ABBREV:
            return True
    return False


def _looks_like_egg_product(desc_n: str, desc_tokens: list[str]) -> bool:
    """True when NFC-e line is primarily eggs (not pasta c/ovos)."""
    if not _EGG_TOKEN.search(desc_n):
        return False
    if _is_pasta_as_egg_noise(desc_n, desc_tokens):
        return False
    idx = _primary_index(desc_tokens, "ovo")
    if idx is None:
        idx = _primary_index(desc_tokens, "ovos")
    # Primary/early product token is egg.
    return idx is not None and idx <= 2


def _volume_liters(
    description: str,
    *,
    quantity: float | None = None,
    unit: str | None = None,
    base_unit: str | None = None,
    quantity_parsed: bool = False,
) -> float | None:
    """Best-effort package volume in liters."""
    if quantity_parsed and base_unit == "L" and quantity is not None:
        # quantity may be in ml if unit is ml — prefer base when available.
        # NormalizedOffer.quantity is in `unit`, not always base.
        from ..normalization.units import to_base

        if unit:
            conv = to_base(quantity, unit)
            if conv and conv[1] == "L":
                return conv[0]
        if base_unit == "L":
            # Some callers pass base already in quantity when unit==L
            return float(quantity)
    pq = extract_quantity(description or "")
    if pq and pq.base_unit == "L":
        return pq.base_value
    return None


def _count_units(
    description: str,
    *,
    quantity: float | None = None,
    unit: str | None = None,
    base_unit: str | None = None,
    quantity_parsed: bool = False,
) -> float | None:
    """Best-effort package count (eggs etc.)."""
    desc_n = _norm(description or "")
    if quantity_parsed and base_unit == "un" and quantity is not None:
        from ..normalization.units import to_base

        if unit:
            conv = to_base(quantity, unit)
            if conv and conv[1] == "un":
                return conv[0]
    pq = extract_quantity(description or "")
    if pq and pq.base_unit == "un":
        return pq.base_value
    # Keyword hints when size parse misses (e.g. bare "DZ").
    if re.search(r"\b(dz|duzia|dúzia)\b", desc_n, re.I):
        return 12.0
    if re.search(r"\bbandeja\b", desc_n):
        return 12.0
    return None


def _mass_kg(
    description: str,
    *,
    quantity: float | None = None,
    unit: str | None = None,
    base_unit: str | None = None,
    quantity_parsed: bool = False,
) -> float | None:
    if quantity_parsed and base_unit == "kg" and quantity is not None:
        from ..normalization.units import to_base

        if unit:
            conv = to_base(quantity, unit)
            if conv and conv[1] == "kg":
                return conv[0]
    pq = extract_quantity(description or "")
    if pq and pq.base_unit == "kg":
        return pq.base_value
    return None


def package_class_rank(
    user_label: str,
    search_term: str = "",
    *,
    description: str = "",
    quantity: float | None = None,
    unit: str | None = None,
    base_unit: str | None = None,
    quantity_parsed: bool = False,
) -> int:
    """Return package-class rank for staples (lower = better grocery match).

    Used by ranking (D1: class before unit_price) and RAG learn guard (D5).
    Non-staple intents return UNKNOWN (neutral).
    """
    intent_n = _norm(f"{user_label} {search_term}".strip())
    desc = description or ""
    desc_n = _norm(desc)
    kw = dict(
        quantity=quantity,
        unit=unit,
        base_unit=base_unit,
        quantity_parsed=quantity_parsed,
    )

    if _is_oil_intent(intent_n):
        if not _query_wants_coco(intent_n) and _COCO.search(desc_n):
            return _CLASS_OUTLIER
        if _OIL_OFF_INTENT.search(desc_n):
            return _CLASS_OUTLIER
        vol = _volume_liters(desc, **kw)
        if vol is None:
            return _CLASS_UNKNOWN
        if vol < _OIL_MIN_L:
            return _CLASS_OUTLIER
        if _OIL_PREF_LO <= vol <= _OIL_PREF_HI and _COOKING_OIL_TYPES.search(desc_n):
            return _CLASS_PREFERRED
        if _OIL_PREF_LO <= vol <= _OIL_PREF_HI:
            return _CLASS_OK
        if 0.2 <= vol < _OIL_PREF_LO or _OIL_PREF_HI < vol <= 2.0:
            return _CLASS_OK
        return _CLASS_DEMOT

    if _is_egg_intent(intent_n):
        if _is_pasta_as_egg_noise(desc_n, _token_list(desc)):
            return _CLASS_OUTLIER
        count = _count_units(desc, **kw)
        if count is None:
            # Single "OVO … UN" often unparsed; demote vs bandeja.
            if re.search(r"\b(un|und|unidade)\b", desc_n) and not re.search(
                r"\b(bandeja|dz|duzia|c/\s*[2-9]|c/\s*[1-9][0-9])\b", desc_n
            ):
                return _CLASS_DEMOT
            return _CLASS_UNKNOWN
        if count >= _EGG_PREF_MIN:
            return _CLASS_PREFERRED
        if count >= 2:
            return _CLASS_OK
        return _CLASS_DEMOT  # single egg

    if _is_sugar_intent(intent_n):
        mass = _mass_kg(desc, **kw)
        if mass is None:
            return _CLASS_UNKNOWN
        if _SUGAR_PREF_LO <= mass <= _SUGAR_PREF_HI:
            return _CLASS_PREFERRED
        if mass < 0.2:
            return _CLASS_OUTLIER
        return _CLASS_OK

    return _CLASS_UNKNOWN


def package_class_ok(
    user_label: str,
    search_term: str = "",
    *,
    description: str = "",
    quantity: float | None = None,
    unit: str | None = None,
    base_unit: str | None = None,
    quantity_parsed: bool = False,
    max_rank: int = _CLASS_OK,
) -> bool:
    """True when package is in-class enough to learn / trust (D5)."""
    rank = package_class_rank(
        user_label,
        search_term,
        description=description,
        quantity=quantity,
        unit=unit,
        base_unit=base_unit,
        quantity_parsed=quantity_parsed,
    )
    return rank <= max_rank


def offer_package_class_rank(
    user_label: str, search_term: str, offer: NormalizedOffer
) -> int:
    return package_class_rank(
        user_label,
        search_term,
        description=offer.description or "",
        quantity=offer.quantity,
        unit=offer.unit,
        base_unit=offer.base_unit,
        quantity_parsed=offer.quantity_parsed,
    )


def offer_package_class_ok(
    user_label: str,
    search_term: str,
    offer: NormalizedOffer,
    *,
    max_rank: int = _CLASS_OK,
) -> bool:
    return package_class_ok(
        user_label,
        search_term,
        description=offer.description or "",
        quantity=offer.quantity,
        unit=offer.unit,
        base_unit=offer.base_unit,
        quantity_parsed=offer.quantity_parsed,
        max_rank=max_rank,
    )


@dataclass(frozen=True)
class RelevanceResult:
    score: float
    kept: list[NormalizedOffer]
    dropped: int


def _hard_reject_score(
    intent_n: str, desc_n: str, desc_tokens: list[str], description: str
) -> float | None:
    """Return a low score for known off-intent SKUs, else None."""
    # P0: non-egg queries must never keep egg SKUs (cross-query bleed).
    if not _is_egg_intent(intent_n) and _looks_like_egg_product(desc_n, desc_tokens):
        return 0.04

    # Eggs: pasta "MAC OVOS" / "C/OVOS" macarrão must never win (W1.2/W1.3).
    if _is_egg_intent(intent_n) and _is_pasta_as_egg_noise(desc_n, desc_tokens):
        return 0.04

    # Plain óleo: coconut oil, saturado, fish-in-oil, tiny sachets (W1.1/W1.3/P0).
    if _is_oil_intent(intent_n) and not _query_wants_coco(intent_n):
        if _COCO.search(desc_n):
            return 0.04
        if _OIL_OFF_INTENT.search(desc_n):
            return 0.04
        vol = _volume_liters(description)
        if vol is not None and vol < _OIL_MIN_L:
            return 0.04
        # Oil must be an early product word (not "SARD … OLEO" tail).
        oil_idx = _primary_index(desc_tokens, "oleo")
        if oil_idx is None or oil_idx > 2:
            return 0.04
        # Prefer real cooking oils; bare "OLEO …" without type is weak unless size OK.
        if not _COOKING_OIL_TYPES.search(desc_n):
            # Allow only if clearly oil pack size and no off-intent already caught.
            if vol is None or not (_OIL_PREF_LO <= vol <= _OIL_PREF_HI):
                return 0.08

    # Table salt: snack chips / "S SAL" castanha / pipoca must not win (P0).
    if _is_salt_intent(intent_n):
        if _SALT_SNACK.search(desc_n):
            return 0.04
        sal_idx = _primary_index(desc_tokens, "sal")
        if sal_idx is None:
            return 0.04
        if sal_idx > 1:
            return 0.04
        # "SALG …" no longer matches via prefix; still require product cue or idx0.
        if sal_idx == 1 and not _SALT_PRODUCT.search(desc_n):
            return 0.08

    # Feijão: "tempero para feijão" is seasoning, not beans (P0).
    if _is_bean_intent(intent_n):
        if _BEAN_SEASONING.search(desc_n):
            return 0.04
        bean_idx = _primary_index(desc_tokens, "feijao")
        if bean_idx is None:
            return 0.04
        if bean_idx > 1:
            return 0.08

    # Açúcar: zero-açúcar candy / party sachets are not crystal sugar (P0).
    if _is_sugar_intent(intent_n):
        if _SUGAR_CANDY.search(desc_n):
            return 0.04
        sugar_idx = _primary_index(desc_tokens, "acucar")
        if sugar_idx is None:
            return 0.04
        if sugar_idx > 1:
            return 0.08

    # Café: caramelos / "coração cafe canela" spice mix (P0).
    if _is_coffee_intent(intent_n):
        if _COFFEE_JUNK.search(desc_n):
            return 0.04
        cafe_idx = _primary_index(desc_tokens, "cafe")
        if cafe_idx is None:
            return 0.04
        # Multi-spice blend listing café as flavor (not coffee product).
        if _COFFEE_SPICE_MIX.search(desc_n) and not _COFFEE_PRODUCT.search(desc_n):
            return 0.04
        if cafe_idx > 1 and not _COFFEE_PRODUCT.search(desc_n):
            return 0.08

    return None


def score_description(user_label: str, search_term: str, description: str) -> float:
    """Score a free-text product description against user intent (0..1)."""
    intent = f"{user_label} {search_term}".strip()
    desc = description or ""
    if not intent or not desc:
        return 0.0

    intent_n = _norm(intent)
    desc_n = _norm(desc)
    intent_toks = _expand_synonyms(_token_set(intent))
    desc_tokens = _token_list(desc)
    desc_toks = _expand_synonyms({t for t in desc_tokens if t not in _STOP})
    if not intent_toks or not desc_toks:
        return 0.0

    content = {t for t in intent_toks if not re.fullmatch(r"\d+[a-z]*", t)}
    if not content:
        content = intent_toks

    overlap = content & desc_toks
    if not overlap:
        return 0.0

    hard = _hard_reject_score(intent_n, desc_n, desc_tokens, desc)
    if hard is not None:
        return hard

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
        # Oil: prefer cooking-size mass oils (soja/girassol 900 ml class).
        if st == "oleo":
            if _COOKING_OIL_TYPES.search(desc_n):
                base += 0.08
            vol = _volume_liters(desc)
            if vol is not None and _OIL_PREF_LO <= vol <= _OIL_PREF_HI:
                base += 0.12
        # Eggs: prefer bandeja/dúzia over single UN.
        if st in ("ovo", "ovos"):
            count = _count_units(desc)
            if count is not None and count >= _EGG_PREF_MIN:
                base += 0.12
            elif count is not None and count <= 1:
                base -= 0.18
            elif re.search(r"\b(bandeja|dz|duzia)\b", desc_n):
                base += 0.12
        # Sugar: prefer 1 kg class.
        if st == "acucar":
            mass = _mass_kg(desc)
            if mass is not None and _SUGAR_PREF_LO <= mass <= _SUGAR_PREF_HI:
                base += 0.10
            elif mass is not None and mass < 0.2:
                base -= 0.20
        # Salt: prefer refinado/grosso 1 kg class.
        if st == "sal":
            if _SALT_PRODUCT.search(desc_n):
                base += 0.18
            mass = _mass_kg(desc)
            if mass is not None and 0.4 <= mass <= 1.5:
                base += 0.10
        # Coffee: prefer torrado/moído/solúvel packs.
        if st == "cafe" and _COFFEE_PRODUCT.search(desc_n):
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
    # Best relevance first; among equals, better package class then cheaper unit.
    scored.sort(
        key=lambda x: (
            -x[0],
            offer_package_class_rank(user_label, search_term, x[1]),
            x[1].unit_price,
            x[1].price,
        )
    )
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
