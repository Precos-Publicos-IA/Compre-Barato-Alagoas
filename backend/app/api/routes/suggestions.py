"""Quick-suggestion buttons for common grocery items (UX: low-friction entry).

Serves both the legacy emoji-based chips and catalog-aware suggestions with
product IDs for the new structured search flow.
"""

from __future__ import annotations

from fastapi import APIRouter

from ...services.catalog.manager import get_catalog

router = APIRouter(prefix="/api/v1", tags=["suggestions"])

# Curated common basket items for the home-screen chips. Emoji aids low-literacy users.
# Maps slug → emoji for products that exist in the catalog.
_EMOJI_MAP = {
    "arroz": "🍚",
    "feijao": "🫘",
    "leite": "🥛",
    "ovo": "🥚",
    "ovos": "🥚",
    "acucar": "🧂",
    "cafe": "☕",
    "oleo": "🛢️",
    "macarrao": "🍝",
    "banana": "🍌",
    "tomate": "🍅",
    "frango": "🍗",
    "refrigerante": "🥤",
}

# Ordered list of slugs to show as suggestions
_SUGGESTED_SLUGS = [
    "arroz", "feijao", "leite", "ovo", "acucar", "cafe",
    "oleo", "macarrao", "banana", "tomate", "frango", "refrigerante",
]


@router.get("/suggestions")
async def suggestions() -> dict:
    """Return quick-suggestion items, now backed by the product catalog."""
    catalog = get_catalog()
    items = []
    for slug in _SUGGESTED_SLUGS:
        product = catalog.get_by_slug(slug)
        if product and product.enabled:
            items.append({
                "label": product.display_name,
                "emoji": _EMOJI_MAP.get(slug, "🛒"),
                "product_id": product.id,
                "slug": product.slug,
                "image_url": product.image_url,
            })
        elif slug in _EMOJI_MAP:
            # Fallback for products not yet in catalog
            items.append({
                "label": slug.replace("_", " ").capitalize(),
                "emoji": _EMOJI_MAP[slug],
            })
    return {"items": items}
