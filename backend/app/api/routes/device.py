"""Pseudo-anonymous device endpoints — login-free server-side state.

A device identifies itself with an opaque high-entropy token it generated and
keeps in secure storage (no account, no password, no portability). This is the
foundation for features that usually need login (e.g. future discount alerts):
the LGPD consent record and the device's saved shopping lists live here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...cache import Cache
from ...config import Settings
from ...schemas.device import ConsentRequest, DeletionResult, DeviceState
from ..deps import get_cache, get_settings_dep, require_device_token

router = APIRouter(prefix="/api/v1/device", tags=["device"])


def _state_from_record(record: dict | None) -> DeviceState:
    if not record:
        return DeviceState(known=False, consented=False)
    consent_at = record.get("consent_at")
    return DeviceState(
        known=True,
        consented=bool(consent_at),
        consent_at=consent_at,
        policy_version=record.get("policy_version"),
        saved_lists=record.get("saved_lists", []),
    )


@router.post("/consent", response_model=DeviceState)
async def grant_consent(
    body: ConsentRequest,
    token: str = Depends(require_device_token),
    cache: Cache = Depends(get_cache),
    settings: Settings = Depends(get_settings_dep),
) -> DeviceState:
    """Record LGPD consent for this device (the legal basis for storing its data).
    Idempotent: re-posting refreshes the record and its idle TTL.

    ``policy_version`` must match the server canonical version so old/forked
    clients cannot register consent against an arbitrary/stale policy (#344).
    """
    if not body.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consentimento não concedido.",
        )
    canonical = settings.policy_version.strip()
    if body.policy_version.strip() != canonical:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Versão da política desatualizada ou inválida. "
                f"Atualize o app e aceite a versão vigente ({canonical})."
            ),
        )
    await cache.register_consent(token, canonical)
    return _state_from_record(await cache.get_device(token))


@router.get("/me", response_model=DeviceState)
async def get_me(
    token: str = Depends(require_device_token),
    cache: Cache = Depends(get_cache),
) -> DeviceState:
    """What the server holds for this device. Returns ``known=false`` if nothing."""
    return _state_from_record(await cache.get_device(token))


@router.delete("/me", response_model=DeletionResult)
async def delete_me(
    token: str = Depends(require_device_token),
    cache: Cache = Depends(get_cache),
) -> DeletionResult:
    """LGPD erasure: delete all server-side data for this device."""
    return DeletionResult(deleted=await cache.delete_device(token))
