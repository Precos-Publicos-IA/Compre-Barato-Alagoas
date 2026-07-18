"""FastAPI dependencies: shared clients and the daily rate limit."""

from __future__ import annotations

import hashlib
import ipaddress
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status

from ..analytics import Analytics
from ..cache import Cache
from ..config import Settings, get_settings
from ..services.llm.base import LLMClient
from ..services.secrets import SecretStore
from ..services.sefaz.base import SefazClient


def get_settings_dep() -> Settings:
    return get_settings()


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


def get_analytics(request: Request) -> Analytics:
    return request.app.state.analytics


def get_sefaz(request: Request) -> SefazClient:
    return request.app.state.sefaz


def get_llm(request: Request) -> LLMClient:
    return request.app.state.llm


def get_secrets(request: Request) -> SecretStore:
    return request.app.state.secrets


# Pseudo-anonymous device identity: the client sends a high-entropy opaque token
# (generated once, kept in the device's secure storage) as a bearer credential.
# Treated like a password — never logged.
_DEVICE_TOKEN_HEADER = "x-device-token"
_MIN_TOKEN_LEN = 32
_MAX_TOKEN_LEN = 128


def _valid_token(token: str) -> bool:
    return (
        _MIN_TOKEN_LEN <= len(token) <= _MAX_TOKEN_LEN
        and all(c in "0123456789abcdefABCDEF" for c in token)
    )


def get_device_token(request: Request) -> str | None:
    """Optional device token (e.g. on /search): returns it only if well-formed."""
    token = request.headers.get(_DEVICE_TOKEN_HEADER)
    return token if token and _valid_token(token) else None


def require_device_token(request: Request) -> str:
    """Mandatory device token for the /device endpoints."""
    token = get_device_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificação do dispositivo ausente ou inválida.",
        )
    return token


# Anonymous usage-measurement id (LGPD: legitimate interest, opt-out). Sent on every
# search unless the user turns off "Estatísticas anônimas de uso" in the app. Deliberately separate
# from the consent device token: it only ever feeds a salted-hash HyperLogLog (aggregate
# unique count), is never linked to lists/identity, and is never logged or stored as-is.
_ANALYTICS_ID_HEADER = "x-analytics-id"


def get_analytics_id(request: Request) -> str | None:
    """Optional anonymous analytics id (same hex shape as the device token)."""
    value = request.headers.get(_ANALYTICS_ID_HEADER)
    return value if value and _valid_token(value) else None


# The IP is personal data (LGPD), so we never store it raw: the rate-limit key holds
# only a salted hash. The salt comes from settings (RATELIMIT_SALT) so production can
# set a private value — a known/static salt would let a Redis dump be re-identified.


def _client_ip(request: Request) -> str:
    """Best-effort client IP (proxy-aware). Used only for rate-limit decisions."""
    # Honour a proxy header (nginx/Caddy sets X-Forwarded-For), else peer address.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _client_id(request: Request, salt: str) -> str:
    ip = _client_ip(request)
    return hashlib.sha256((salt + ip).encode()).hexdigest()[:32]


def _parse_whitelist(raw: str) -> list:
    """Parse comma-separated IPs/CIDRs; skip invalid entries."""
    out: list = []
    for part in (raw or "").split(","):
        entry = part.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                out.append(ipaddress.ip_network(entry, strict=False))
            else:
                out.append(ipaddress.ip_address(entry))
        except ValueError:
            continue
    return out


def _ip_is_whitelisted(ip: str, settings: Settings) -> bool:
    """Lab/ops IPs skip the daily search quota (dev + configured prod whitelist)."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False

    # Local/dev: never rate-limit loopback or private LAN (CI, docker, office lab).
    env = (settings.environment or "").strip().lower()
    if env not in ("production", "prod"):
        if addr.is_loopback or addr.is_private or addr.is_link_local:
            return True

    for entry in _parse_whitelist(settings.ratelimit_whitelist_ips):
        if isinstance(entry, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
            if addr in entry:
                return True
        elif addr == entry:
            return True
    return False


async def enforce_rate_limit(
    request: Request,
    settings: Settings = Depends(get_settings_dep),
    cache: Cache = Depends(get_cache),
) -> None:
    if settings.daily_search_limit <= 0:
        return
    if _ip_is_whitelisted(_client_ip(request), settings):
        return
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    key = f"ratelimit:{today}:{_client_id(request, settings.ratelimit_salt)}"
    count = await cache.incr_with_ttl(key, ttl=24 * 60 * 60)
    if count > settings.daily_search_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite diário de buscas atingido. Tente novamente amanhã.",
        )
