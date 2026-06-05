"""Request/response schemas for the public search API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    items: list[str] = Field(..., min_length=1, max_length=30)
    latitude: float | None = None
    longitude: float | None = None
    radius_km: int | None = Field(default=None, ge=1, le=15)  # SEFAZ limit
    days: int | None = Field(default=None, ge=1, le=10)        # SEFAZ limit

    @field_validator("items")
    @classmethod
    def _clean_items(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        if not cleaned:
            raise ValueError("at least one non-empty item is required")
        return cleaned


class ItemOffer(BaseModel):
    query: str
    found: bool
    description: str | None = None
    gtin: str | None = None
    price: float | None = None            # package price (what you pay)
    unit_price: float | None = None       # price per base_unit (fair comparison)
    base_unit: str | None = None          # kg | L | un
    quantity: float | None = None
    unit: str | None = None
    unidade_medida: str | None = None
    sale_date: str | None = None
    quantity_parsed: bool = False


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
    total: float                          # sum of package prices for found items
    items: list[ItemOffer]
    missing: list[str] = Field(default_factory=list)


class SearchMetrics(BaseModel):
    items_requested: int
    stores_found: int
    match_rate: float                     # fraction of requested items matched anywhere
    quantity_parse_rate: float            # fraction of matched offers with a parsed size


class Origin(BaseModel):
    latitude: float
    longitude: float


class SearchResponse(BaseModel):
    origin: Origin
    radius_km: int
    days: int
    items_requested: int
    data_source: str                      # "mock" | "sefaz"
    list_id: str | None = None            # shareable UUID for this shopping list
    stores: list[StoreResult]
    metrics: SearchMetrics


class SavedList(BaseModel):
    """A shopping list resolved from a shareable link UUID."""

    items: list[str]
