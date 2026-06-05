"""Quick-suggestion buttons for common grocery items (UX: low-friction entry)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["suggestions"])

# Curated common basket items for the home-screen chips. Emoji aids low-literacy users.
_COMMON_ITEMS = [
    {"label": "Arroz", "emoji": "🍚"},
    {"label": "Feijão", "emoji": "🫘"},
    {"label": "Leite", "emoji": "🥛"},
    {"label": "Ovo", "emoji": "🥚"},
    {"label": "Açúcar", "emoji": "🧂"},
    {"label": "Café", "emoji": "☕"},
    {"label": "Óleo", "emoji": "🛢️"},
    {"label": "Macarrão", "emoji": "🍝"},
    {"label": "Banana", "emoji": "🍌"},
    {"label": "Tomate", "emoji": "🍅"},
    {"label": "Frango", "emoji": "🍗"},
    {"label": "Refrigerante", "emoji": "🥤"},
]


@router.get("/suggestions")
async def suggestions() -> dict:
    return {"items": _COMMON_ITEMS}
