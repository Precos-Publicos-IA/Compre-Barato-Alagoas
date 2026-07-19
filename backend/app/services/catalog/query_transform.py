"""Input-to-query transformation: product selections → SEFAZ query terms.

Takes structured user input (list of product IDs + optional size/brand filters)
and produces the SEFAZ query plan. Each product maps to one or more SEFAZ
search queries based on its ``search_queries`` list and any brand/size refinements.
"""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass, field

from .manager import CatalogManager, ProductEntry

logger = logging.getLogger(__name__)


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c)).lower().strip()


@dataclass
class ProductSelection:
    """One user-selected product with optional size/brand filters."""

    product_id: int
    quantity: int = 1
    selected_sizes: list[str] | None = None   # None = any size
    selected_brands: list[str] | None = None  # None = any brand


@dataclass
class SefazQueryPlan:
    """A single SEFAZ query to execute."""

    product_id: int
    product_slug: str
    display_name: str
    search_term: str          # what to send to SEFAZ descricao parameter
    quantity: int = 1
    size_filter: str | None = None   # post-filter on results
    brand_filter: str | None = None  # post-filter on results


@dataclass
class QueryPlanResult:
    """The full list of SEFAZ queries to run for a user's shopping list."""

    queries: list[SefazQueryPlan] = field(default_factory=list)
    # Products that couldn't be resolved (unknown IDs)
    unresolved: list[int] = field(default_factory=list)


def build_query_plan(
    selections: list[ProductSelection],
    catalog: CatalogManager,
) -> QueryPlanResult:
    """Transform a list of product selections into SEFAZ query plans.

    Each product entry has ``search_queries`` — the SEFAZ search terms that
    reliably find this product.  When the user applies brand or size filters,
    we append the filter keyword to the search term to narrow SEFAZ results.
    """
    result = QueryPlanResult()

    for sel in selections:
        product = catalog.get(sel.product_id)
        if product is None:
            result.unresolved.append(sel.product_id)
            continue

        if not product.enabled:
            result.unresolved.append(sel.product_id)
            continue

        # Base search queries for this product
        base_queries = product.search_queries or [_strip_accents(product.display_name)]

        # If user selected specific brands, create queries per brand
        if sel.selected_brands:
            for brand in sel.selected_brands:
                brand_norm = _strip_accents(brand)
                # Use the first (best) search query + brand
                base = base_queries[0]
                search_term = f"{base} {brand_norm}".strip()
                result.queries.append(
                    SefazQueryPlan(
                        product_id=product.id,
                        product_slug=product.slug,
                        display_name=product.display_name,
                        search_term=search_term,
                        quantity=sel.quantity,
                        brand_filter=brand,
                        size_filter=(
                            sel.selected_sizes[0] if sel.selected_sizes else None
                        ),
                    )
                )
        else:
            # No brand filter — use all configured search queries
            # (multiple queries improve coverage of different NFC-e naming styles)
            for query in base_queries[:3]:  # Cap at 3 queries per product
                result.queries.append(
                    SefazQueryPlan(
                        product_id=product.id,
                        product_slug=product.slug,
                        display_name=product.display_name,
                        search_term=query,
                        quantity=sel.quantity,
                        size_filter=(
                            sel.selected_sizes[0] if sel.selected_sizes else None
                        ),
                    )
                )

    return result
