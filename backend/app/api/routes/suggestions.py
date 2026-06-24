"""Quick-suggestion buttons for common grocery items (UX: low-friction entry).

Default list lives in ``config.DEFAULT_SUGGESTION_ITEMS``; operators can override
via ``SUGGESTIONS_JSON`` env without code changes (#309). Admin/runtime editor
can build on this later (Redis-backed config).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...config import Settings
from ..deps import get_settings_dep

router = APIRouter(prefix="/api/v1", tags=["suggestions"])


@router.get("/suggestions")
async def suggestions(settings: Settings = Depends(get_settings_dep)) -> dict:
    return {"items": settings.suggestion_items}
