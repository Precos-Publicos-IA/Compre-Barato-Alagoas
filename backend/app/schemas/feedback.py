"""Schemas for user feedback on search results (drives the admin dashboard)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

FeedbackKind = Literal["helpful", "wrong_item", "other"]
FEEDBACK_KINDS: frozenset[str] = frozenset({"helpful", "wrong_item", "other"})

# Shareable list ids are uuid4.hex (32 hex chars) — same rule as GET /lists/{id} (#392).
_LIST_ID_LEN = 32


def _valid_list_id(list_id: str) -> bool:
    return (
        len(list_id) == _LIST_ID_LEN
        and all(c in "0123456789abcdefABCDEF" for c in list_id)
    )


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
        None,
        max_length=32,
        description="Share list UUID (32 hex chars), if any.",
    )

    @field_validator("list_id")
    @classmethod
    def _list_id_hex(cls, v: str | None) -> str | None:
        if v is None:
            return None
        t = v.strip()
        if not t:
            return None
        if not _valid_list_id(t):
            raise ValueError("list_id must be a 32-character hex share id")
        return t.lower()


class FeedbackAck(BaseModel):
    recorded: bool = True
