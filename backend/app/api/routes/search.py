"""The main basket search endpoint (+ progressive NDJSON stream)."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

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


def _json_line(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, default=str) + "\n").encode("utf-8")


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
            favorite_cnpjs=set(req.favorite_cnpjs or []),
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


@router.post(
    "/search/stream",
    dependencies=[Depends(enforce_rate_limit)],
)
async def search_stream(
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
):
    """NDJSON progressive search.

    Lines are JSON objects:
      {"type":"status","message":"...","items_completed":0,"items_total":3}
      {"type":"partial","response":{...SearchResponse partial...}}
      {"type":"done","response":{...final SearchResponse...}}
      {"type":"error","detail":"..."}
    """
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_progress(ev: dict) -> None:
        msg = {
            "type": "status",
            "message": ev.get("message"),
            "phase": ev.get("phase"),
            "items_completed": ev.get("items_completed"),
            "items_total": ev.get("items_total"),
        }
        await queue.put(msg)
        partial = ev.get("partial_response")
        if partial is not None:
            await queue.put(
                {
                    "type": "partial",
                    "response": partial.model_dump(mode="json"),
                }
            )

    async def worker() -> None:
        try:
            result = await run_search(
                req,
                settings=settings,
                sefaz=sefaz,
                llm=llm,
                cache=cache,
                analytics=analytics,
                device_token=device_token,
                analytics_id=analytics_id,
                background=background,
                on_progress=on_progress,
                favorite_cnpjs=set(req.favorite_cnpjs or []),
            )
            await queue.put(
                {"type": "done", "response": result.model_dump(mode="json")}
            )
        except HTTPException as he:
            await queue.put(
                {"type": "error", "detail": he.detail, "status": he.status_code}
            )
        except Exception:
            rid = getattr(getattr(request, "state", None), "request_id", None)
            logger.exception("search stream failed rid=%s", rid)
            ref = f" (ref: {rid})" if rid else ""
            await queue.put(
                {
                    "type": "error",
                    "detail": f"Não foi possível consultar os preços agora. Tente novamente.{ref}",
                    "status": 502,
                }
            )
        finally:
            await queue.put(None)

    async def gen():
        task = asyncio.create_task(worker())
        try:
            yield _json_line(
                {
                    "type": "status",
                    "message": "Iniciando busca…",
                    "phase": "start",
                    "items_completed": 0,
                    "items_total": len(req.items),
                }
            )
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield _json_line(item)
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@router.get(
    "/lists/{list_id}",
    response_model=SavedList,
    dependencies=[Depends(enforce_rate_limit)],
)
async def get_list(
    list_id: str,
    cache: Cache = Depends(get_cache),
) -> SavedList:
    """Resolve a shareable link UUID back into its shopping list."""
    items = await cache.get_search_list(list_id)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista não encontrada ou expirada.",
        )
    return SavedList(items=items)
