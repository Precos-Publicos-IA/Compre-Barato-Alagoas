"""Request/response schemas for the public search API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Loose Brazil bounding box. The app is Alagoas-focused, but legitimate origins can
# sit just outside the state line, so we sanity-check against the whole country
# rather than a tight AL box. Anything outside this is spoofed/garbage and must not
# reach SEFAZ/LLM (off-region cost + abuse). See issue #334.
_BR_LAT_MIN, _BR_LAT_MAX = -34.0, 6.0
_BR_LON_MIN, _BR_LON_MAX = -74.5, -33.0

# Max characters per basket item. Grocery labels are short; anything longer is paste/
# voice/share abuse pushing multi-KB strings into SEFAZ/LLM/analytics (issue #369).
_MAX_ITEM_LEN = 120


class SearchRequest(BaseModel):
    items: list[str] = Field(..., min_length=1, max_length=30)
    latitude: float | None = None
    longitude: float | None = None
    radius_km: int | None = Field(default=None, ge=1, le=15)  # SEFAZ limit
    days: int | None = Field(default=None, ge=1, le=10)        # SEFAZ limit
    # CNPJs the user chose to hide (app: "lojas ocultas"). Filtered server-side *before*
    # top-N truncation so a hidden store never silently eats a result slot. Ephemeral:
    # used only to filter this request, never logged or persisted.
    excluded_cnpjs: list[str] = Field(default_factory=list, max_length=200)
    # Optional client favorites — soft ranking boost when coverage ties.
    favorite_cnpjs: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("items")
    @classmethod
    def _clean_items(cls, v: list[str]) -> list[str]:
        # Trim, drop empties, and cap each label so a single oversized line can't
        # balloon downstream SEFAZ/LLM/analytics payloads (#369).
        cleaned = [s.strip()[:_MAX_ITEM_LEN] for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("at least one non-empty item is required")
        return cleaned

    @field_validator("latitude")
    @classmethod
    def _check_lat(cls, v: float | None) -> float | None:
        if v is not None and not (_BR_LAT_MIN <= v <= _BR_LAT_MAX):
            raise ValueError("latitude fora dos limites do Brasil")
        return v

    @field_validator("longitude")
    @classmethod
    def _check_lon(cls, v: float | None) -> float | None:
        if v is not None and not (_BR_LON_MIN <= v <= _BR_LON_MAX):
            raise ValueError("longitude fora dos limites do Brasil")
        return v


class ItemOffer(BaseModel):
    query: str
    found: bool
    description: str | None = None
    gtin: str | None = None
    price: float | None = None            # package price (what you pay for one)
    unit_price: float | None = None       # price per base_unit (fair comparison)
    base_unit: str | None = None          # kg | L | un
    quantity: float | None = None
    unit: str | None = None
    unidade_medida: str | None = None
    sale_date: str | None = None
    quantity_parsed: bool = False
    requested_quantity: int = 1           # how many of this item the user asked for
    line_total: float | None = None       # price * requested_quantity (cost of the line)
    # Human package hint, e.g. "5 kg" or "1 L" (for UI without client-side math).
    package_label: str | None = None
    # True when this is the store's best match for the query (always true today;
    # reserved if we later return runners-up).
    is_best_match: bool = True


class StoreResult(BaseModel):
    cnpj: str
    name: str
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    bairro: str | None = None
    distance_km: float | None = None
    items_found: int
    items_total: int
    total: float                          # sum of (price * requested_quantity) for found items
    items: list[ItemOffer]
    missing: list[str] = Field(default_factory=list)
    # Short PT reason for ranking position, e.g. "Mais barato com 3/3 itens".
    rank_reason: str | None = None
    # Soft boost flag when store is in the user's favorites (client-ordered too).
    is_favorite: bool = False


class SearchRewrite(BaseModel):
    """How we turned a vague user term into the SEFAZ/web search_term."""

    label: str
    original: str
    search_term: str


class SearchMetrics(BaseModel):
    items_requested: int
    stores_found: int
    match_rate: float                     # fraction of requested items matched anywhere
    quantity_parse_rate: float            # fraction of matched offers with a parsed size
    # Added by Verifier agent: helpful rewrites for items the user typed vaguely.
    # Audience-friendly: shows things like "pão" -> "pão francês" so poor users
    # who don't know exact names still get results next time or see tips.
    suggested_refinements: list[str] = Field(default_factory=list)
    # What we actually searched (when different from the typed label).
    search_rewrites: list[SearchRewrite] = Field(default_factory=list)
    # Progress helpers for progressive UX (optional on final response).
    items_completed: int | None = None
    status_message: str | None = None


class Origin(BaseModel):
    latitude: float
    longitude: float


class SearchResponse(BaseModel):
    origin: Origin
    radius_km: int
    days: int
    items_requested: int
    data_source: str                      # "mock" | "sefaz" | "web"
    list_id: str | None = None            # shareable UUID for this shopping list
    stores: list[StoreResult]
    metrics: SearchMetrics
    # Always-on honesty: NFC-e prices may differ from the shelf.
    data_disclaimer: str = (
        "Preços de vendas recentes (NFC-e). Podem diferir na loja."
    )
    # True while a progressive stream is still fetching more items.
    partial: bool = False


class SavedList(BaseModel):
    """A shopping list resolved from a shareable link UUID."""

    items: list[str]
