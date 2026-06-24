"""Schemas for user feedback on search results (drives the admin dashboard)."""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, field_validator

FeedbackKind = Literal["helpful", "wrong_item", "other"]

# Strip C0/C1 controls (except common whitespace we normalise separately) (#198).
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def _sanitize_user_text(value: str | None, *, max_len: int) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", value)
    text = _CTRL_RE.sub("", text)
    # Collapse runs of whitespace; keep it as a single line for storage/logs.
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    # Defence-in-depth if any consumer ever interpolates without escaping (#133).
    text = text.replace("<", "").replace(">", "")
    if len(text) > max_len:
        text = text[:max_len]
    return text or None


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

    @field_validator("item", "note", mode="before")
    @classmethod
    def _clean_optional_text(cls, v: object) -> object:
        if v is None or not isinstance(v, str):
            return v
        # max_len applied again in model; use generous intermediate then Field clips.
        return v

    @field_validator("item")
    @classmethod
    def _sanitize_item(cls, v: str | None) -> str | None:
        return _sanitize_user_text(v, max_len=120)

    @field_validator("note")
    @classmethod
    def _sanitize_note(cls, v: str | None) -> str | None:
        return _sanitize_user_text(v, max_len=500)


class FeedbackAck(BaseModel):
    recorded: bool = True
