"""The main basket search endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from ...analytics import Analytics
from ...cache import Cache
from ...config import Settings
from ...schemas.search import SavedList, SearchRequest, SearchResponse
from ...services.llm.base import LLMClient
from ...services.search_service import run_search
from ...services.sefaz.base import SefazClient
from ..deps import (
    enforce_rate_limit,
    get_analytics,
    get_analytics_id,
    get_cache,
    get_device_token,
    get_llm,
    get_sefaz,
    get_settings_dep,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["search"])

# Shareable list IDs are minted as uuid.uuid4().hex (32 hex chars) (#381 / #390).
_LIST_ID_LEN = 32


def _valid_list_id(list_id: str) -> bool:
    return (
        len(list_id) == _LIST_ID_LEN
        and all(c in "0123456789abcdefABCDEF" for c in list_id)
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(enforce_rate_limit)],
)
async def search(
    req: SearchRequest,
    background: BackgroundTasks,
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    sefaz: SefazClient = Depends(get_sefaz),
    llm: LLMClient = Depends(get_llm),
    cache: Cache = Depends(get_cache),
    analytics: Analytics = Depends(get_analytics),
    device_token: str | None = Depends(get_device_token),
    analytics_id: str | None = Depends(get_analytics_id),
) -> SearchResponse:
    try:
        return await run_search(
            req,
            settings=settings,
            sefaz=sefaz,
            llm=llm,
            cache=cache,
            analytics=analytics,
            device_token=device_token,
            analytics_id=analytics_id,
            background=background,
        )
    except HTTPException:
        raise
    except Exception:
        rid = getattr(getattr(request, "state", None), "request_id", None)
        logger.exception("search failed rid=%s", rid)
        ref = f" (ref: {rid})" if rid else ""
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Não foi possível consultar os preços agora. Tente novamente.{ref}",
        )


@router.get(
    "/lists/{list_id}",
    response_model=SavedList,
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_list(
    list_id: str,
    cache: Cache = Depends(get_cache),
) -> SavedList:
    """Resolve a shareable link UUID back into its shopping list.

    404 once the list has expired (30 idle days) so the app can send the user
    back to the home screen. Malformed ids are 400 before Redis (#381).
    """
    if not _valid_list_id(list_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de lista inválido.",
        )
    items = await cache.get_search_list(list_id)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista não encontrada ou expirada.",
        )
    return SavedList(items=items)
