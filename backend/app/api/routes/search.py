"""The main basket search endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ...cache import Cache
from ...config import Settings
from ...schemas.search import SavedList, SearchRequest, SearchResponse
from ...services.llm.base import LLMClient
from ...services.search_service import run_search
from ...services.sefaz.base import SefazClient
from ..deps import (
    enforce_rate_limit,
    get_cache,
    get_llm,
    get_sefaz,
    get_settings_dep,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def search(
    req: SearchRequest,
    settings: Settings = Depends(get_settings_dep),
    sefaz: SefazClient = Depends(get_sefaz),
    llm: LLMClient = Depends(get_llm),
    cache: Cache = Depends(get_cache),
) -> SearchResponse:
    try:
        return await run_search(
            req, settings=settings, sefaz=sefaz, llm=llm, cache=cache
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("search failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível consultar os preços agora. Tente novamente.",
        )


@router.get("/lists/{list_id}", response_model=SavedList)
async def get_list(
    list_id: str,
    cache: Cache = Depends(get_cache),
) -> SavedList:
    """Resolve a shareable link UUID back into its shopping list.

    404 once the list has expired (30 idle days) so the app can send the user
    back to the home screen.
    """
    items = await cache.get_search_list(list_id)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista não encontrada ou expirada.",
        )
    return SavedList(items=items)
