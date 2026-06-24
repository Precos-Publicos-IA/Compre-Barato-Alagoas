"""Schemas for user feedback on search results (drives the admin dashboard)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

FeedbackKind = Literal["helpful", "wrong_item", "other"]


def _strip_control_chars(v: str | None) -> str | None:
    """Drop control characters (keep \\t \\n \\r) from free text before it is stored
    and later rendered in the admin dashboard. Defense in depth alongside the admin
    SPA's HTML escaping — keeps NUL/escape/terminal sequences out of logs and the
    Redis-backed feedback stream (issue #198)."""
    if v is None:
        return None
    cleaned = "".join(
        c for c in v if c in ("\t", "\n", "\r") or (ord(c) >= 32 and ord(c) != 127)
    ).strip()
    return cleaned or None


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

    @field_validator("item", "note")
    @classmethod
    def _sanitize_text(cls, v: str | None) -> str | None:
        return _strip_control_chars(v)


class FeedbackAck(BaseModel):
    recorded: bool = True
