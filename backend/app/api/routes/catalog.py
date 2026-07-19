"""API routes for the product catalog (enum) system.

Provides:
- GET /api/v1/catalog/products — full product list for device-side caching
- GET /api/v1/catalog/products/search — quick search for the product selector
- GET /api/v1/catalog/products/{product_id} — single product details
- GET /api/v1/catalog/categories — all categories
- POST /api/v1/catalog/products/request — request a new product
- POST /api/v1/catalog/search — structured search with product selections
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...config import Settings
from ...schemas.search import SearchResponse
from ...services.catalog.manager import get_catalog
from ...services.catalog.query_transform import ProductSelection
from ...services.catalog.search import run_catalog_search
from ..deps import (
    enforce_rate_limit,
    get_cache,
    get_catalog_dep,
    get_flag_store_dep,
    get_sefaz,
    get_settings_dep,
    get_validation_llm,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


# --- Response models ---

class ProductBrief(BaseModel):
    id: int
    slug: str
    display_name: str
    category: str
    image_url: str | None = None
    brands: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ProductDetail(ProductBrief):
    sefaz_terms_positive: list[str] = Field(default_factory=list)
    sefaz_terms_negative: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    enabled: bool = True


class ProductListResponse(BaseModel):
    products: list[ProductBrief]
    total: int


class CategoryListResponse(BaseModel):
    categories: list[str]


class ProductRequestInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    requested_by: str | None = None


class ProductRequestResponse(BaseModel):
    name: str
    status: str
    message: str


class ProductSelectionInput(BaseModel):
    """One product selection for the structured search."""
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)
    selected_sizes: list[str] | None = None
    selected_brands: list[str] | None = None


class CatalogSearchRequest(BaseModel):
    """Structured search request using product catalog IDs."""
    selections: list[ProductSelectionInput] = Field(..., min_length=1, max_length=30)
    latitude: float | None = None
    longitude: float | None = None
    radius_km: int | None = Field(default=None, ge=1, le=15)
    days: int | None = Field(default=None, ge=1, le=10)
    excluded_cnpjs: list[str] = Field(default_factory=list, max_length=200)
    favorite_cnpjs: list[str] = Field(default_factory=list, max_length=200)


# --- Routes ---

@router.get("/products", response_model=ProductListResponse)
async def list_products(
    category: str | None = None,
    q: str | None = None,
    limit: int = 200,
):
    """List all products in the catalog (for device-side caching).

    Optional filters:
    - category: filter by category
    - q: search query (prefix/substring)
    """
    catalog = get_catalog()

    if q:
        products = catalog.search(q, limit=limit)
    elif category:
        products = catalog.products_by_category(category)
    else:
        products = catalog.all_products()

    briefs = [
        ProductBrief(
            id=p.id,
            slug=p.slug,
            display_name=p.display_name,
            category=p.category,
            image_url=p.image_url,
            brands=p.brands,
            sizes=p.sizes,
        )
        for p in products[:limit]
    ]

    return ProductListResponse(products=briefs, total=len(briefs))


@router.get("/products/search")
async def search_products(q: str, limit: int = 20):
    """Quick search for the device product selector.

    Returns products matching the query by prefix or substring,
    ordered by relevance.
    """
    catalog = get_catalog()
    products = catalog.search(q, limit=limit)

    return {
        "results": [
            {
                "id": p.id,
                "slug": p.slug,
                "display_name": p.display_name,
                "category": p.category,
                "image_url": p.image_url,
                "brands": p.brands,
                "sizes": p.sizes,
            }
            for p in products
        ]
    }


@router.get("/products/{product_id}", response_model=ProductDetail)
async def get_product(product_id: int):
    """Get full details for a product, including SEFAZ terms."""
    catalog = get_catalog()
    product = catalog.get(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado",
        )
    return ProductDetail(
        id=product.id,
        slug=product.slug,
        display_name=product.display_name,
        category=product.category,
        image_url=product.image_url,
        brands=product.brands,
        sizes=product.sizes,
        sefaz_terms_positive=product.sefaz_terms_positive,
        sefaz_terms_negative=product.sefaz_terms_negative,
        search_queries=product.search_queries,
        enabled=product.enabled,
    )


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories():
    """List all product categories."""
    catalog = get_catalog()
    return CategoryListResponse(categories=catalog.categories())


@router.post("/products/request", response_model=ProductRequestResponse)
async def request_product(req: ProductRequestInput):
    """Request a new product be added to the catalog.

    The request is queued for review by the daily training job.
    It is NOT immediately added to the catalog.
    """
    catalog = get_catalog()

    # Check if it already exists
    matches = catalog.search(req.name, limit=3)
    for m in matches:
        if m.slug == req.name.lower().replace(" ", "_"):
            return ProductRequestResponse(
                name=req.name,
                status="duplicate",
                message=f"Produto já existe: {m.display_name}",
            )

    catalog.add_request(req.name, requested_by=req.requested_by)

    return ProductRequestResponse(
        name=req.name,
        status="pending",
        message="Seu pedido foi registrado e será avaliado em breve.",
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def catalog_search(
    req: CatalogSearchRequest,
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    sefaz=Depends(get_sefaz),
    cache=Depends(get_cache),
    catalog=Depends(get_catalog_dep),
    flag_store=Depends(get_flag_store_dep),
    validation_llm=Depends(get_validation_llm),
) -> SearchResponse:
    """Structured catalog search: product selections -> SEFAZ -> validated results.

    This is the reachable entry point for the catalog-based pipeline (the old
    free-text ``/api/v1/search`` remains for backward compatibility).
    """
    if req.latitude is None or req.longitude is None:
        raise HTTPException(
            status_code=422,
            detail="latitude e longitude são obrigatórias.",
        )

    selections = [
        ProductSelection(
            product_id=s.product_id,
            quantity=s.quantity,
            selected_sizes=s.selected_sizes,
            selected_brands=s.selected_brands,
        )
        for s in req.selections
    ]

    try:
        return await run_catalog_search(
            selections,
            catalog=catalog,
            sefaz=sefaz,
            llm_client=validation_llm,
            redis=cache.redis,
            settings=settings,
            lat=req.latitude,
            lon=req.longitude,
            radius_km=req.radius_km,
            days=req.days,
            excluded_cnpjs=set(req.excluded_cnpjs or []),
            favorite_cnpjs=set(req.favorite_cnpjs or []),
            flag_store=flag_store,
        )
    except HTTPException:
        raise
    except Exception:
        rid = getattr(getattr(request, "state", None), "request_id", None)
        logger.exception("catalog search failed rid=%s", rid)
        ref = f" (ref: {rid})" if rid else ""
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Não foi possível consultar os preços agora. Tente novamente.{ref}",
        )
