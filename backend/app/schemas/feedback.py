"""Schemas for user feedback on search results (drives the admin dashboard)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FeedbackKind = Literal["helpful", "wrong_item", "other"]


class FeedbackRequest(BaseModel):
    kind: FeedbackKind = Field(..., description="What the feedback is about.")
    helpful: bool | None = Field(
        None, description="Thumbs up/down for a results screen (kind='helpful')."
    )
    item: str | None = Field(
        None, max_length=120, description="Item the feedback refers to, if any."
    )
    note: str | None = Field(
        None, max_length=500, description="Optional free-text note from the user."
    )
    list_id: str | None = Field(
        None, max_length=64, description="The searched list this refers to, if any."
    )


class FeedbackAck(BaseModel):
    recorded: bool = True
