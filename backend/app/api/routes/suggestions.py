"""Quick-suggestion buttons for common grocery items (UX: low-friction entry)."""

from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

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

_PAYLOAD = {"items": _COMMON_ITEMS}
_BODY = json.dumps(_PAYLOAD, ensure_ascii=False, separators=(",", ":"))
_ETAG = '"' + hashlib.sha256(_BODY.encode()).hexdigest()[:16] + '"'


@router.get("/suggestions")
async def suggestions(request: Request) -> Response:
    """Static list with HTTP caching so mobile home screens avoid repeat RTTs (#374)."""
    inm = request.headers.get("if-none-match", "").strip()
    if inm == _ETAG:
        return Response(status_code=304, headers={"ETag": _ETAG})
    return JSONResponse(
        content=_PAYLOAD,
        headers={
            "Cache-Control": "public, max-age=3600",
            "ETag": _ETAG,
        },
    )
