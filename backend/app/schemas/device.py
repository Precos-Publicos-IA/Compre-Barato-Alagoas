"""Schemas for the pseudo-anonymous device API (consent + saved lists, no login)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConsentRequest(BaseModel):
    accepted: bool = Field(..., description="Must be true to grant consent.")
    policy_version: str = Field(..., min_length=1, max_length=32)


class DeviceState(BaseModel):
    """What the server knows about a device. Empty for an unknown/erased token."""

    known: bool
    consented: bool
    consent_at: str | None = None
    policy_version: str | None = None
    saved_lists: list[str] = Field(default_factory=list)


class DeletionResult(BaseModel):
    deleted: bool
