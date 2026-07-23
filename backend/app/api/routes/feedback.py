"""User feedback on search results.

Login-free: an optional device token associates feedback with a device, but it's
never required. Feedback is stored Redis-native via Analytics and surfaced on the
admin dashboard so we can spot patterns in bad AI normalization.

``wrong_item`` also goes through ``learn_policy.on_user_feedback`` so RAG
mappings are demoted (Phase 3) — analytics alone is not enough.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from ...analytics import Analytics
from ...cache import Cache
from ...schemas.feedback import FeedbackAck, FeedbackRequest
from ...services.rag.learn_policy import on_user_feedback
from ..deps import enforce_rate_limit, get_analytics, get_cache, get_device_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackAck,
    # Same IP-hash daily bucket as search/lists — stops unauthenticated spam (#137).
    dependencies=[Depends(enforce_rate_limit)],
)
async def submit_feedback(
    body: FeedbackRequest,
    analytics: Analytics = Depends(get_analytics),
    cache: Cache = Depends(get_cache),
    device_token: str | None = Depends(get_device_token),
) -> FeedbackAck:
    del device_token  # reserved for future per-device feedback correlation
    await analytics.record_feedback(
        kind=body.kind,
        helpful=body.helpful,
        item=body.item,
        note=body.note,
        list_id=body.list_id,
    )
    # Production RAG mutations for wrong_item go through learn_policy only.
    query = (body.item or "").strip()
    if body.kind == "wrong_item" and query:
        try:
            await on_user_feedback(
                cache.rag_store(),
                kind=body.kind,
                query=query,
                description=body.note,
                list_id=body.list_id,
            )
        except Exception:  # pragma: no cover — never fail the ACK on learn
            logger.exception("learn_policy on_user_feedback failed")
    return FeedbackAck(recorded=True)
