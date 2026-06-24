"""User feedback on search results.

Login-free: an optional device token associates feedback with a device, but it's
never required. Feedback is stored Redis-native via Analytics and surfaced on the
admin dashboard so we can spot patterns in bad AI normalization.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...analytics import Analytics
from ...schemas.feedback import FeedbackAck, FeedbackRequest
from ..deps import (
    enforce_rate_limit,
    get_analytics,
    get_analytics_id,
    get_device_token,
)

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
    # Optional headers: device bearer (consented clients) + non-credential analytics id.
    # Stored only as device_fp hash / analytics_id in the stream (#354/#355).
    device_token: str | None = Depends(get_device_token),
    analytics_id: str | None = Depends(get_analytics_id),
) -> FeedbackAck:
    await analytics.record_feedback(
        kind=body.kind,
        helpful=body.helpful,
        item=body.item,
        note=body.note,
        list_id=body.list_id,
        device_token=device_token,
        analytics_id=analytics_id,
    )
    return FeedbackAck(recorded=True)
