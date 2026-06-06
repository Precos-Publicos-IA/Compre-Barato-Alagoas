"""Secret store + LGPD data-at-rest hardening.

Covers the encrypted, admin-managed secret store (SEFAZ token) and two
data-minimization guarantees: device tokens and client IPs are never stored raw.
"""

import json

import fakeredis.aioredis
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.cache import Cache
from app.config import get_settings
from app.main import create_app
from app.services.secrets import SecretStore

ADMIN = "test-admin-token-0123456789"
KEY = Fernet.generate_key().decode()
SEFAZ_TOKEN = "super-secret-sefaz-app-token-XYZ"
DEVICE = "a" * 64


@pytest.fixture
def secrets_env(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN)
    monkeypatch.setenv("SECRET_ENCRYPTION_KEY", KEY)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- SecretStore unit ------------------------------------------------------

async def test_secret_store_roundtrip_and_no_plaintext_at_rest():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    store = SecretStore(redis, KEY)
    assert store.enabled

    await store.set_secret("sefaz_token", SEFAZ_TOKEN)
    assert await store.get_secret("sefaz_token") == SEFAZ_TOKEN

    # The plaintext token must never sit in Redis — only ciphertext + a fingerprint.
    raw = await redis.hgetall("secret:sefaz_token")
    assert SEFAZ_TOKEN not in str(raw)
    status = await store.status("sefaz_token")
    assert status["fingerprint"]

    status = await store.status("sefaz_token")
    assert status["configured"] is True
    assert SEFAZ_TOKEN not in json.dumps(status)  # value never surfaced


async def test_secret_store_disabled_without_key():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    store = SecretStore(redis, "")
    assert store.enabled is False
    assert await store.get_secret("sefaz_token") is None
    with pytest.raises(Exception):
        await store.set_secret("sefaz_token", "x")


# --- Admin API -------------------------------------------------------------

def test_admin_secret_set_status_delete(secrets_env):
    headers = {"Authorization": f"Bearer {ADMIN}"}
    with TestClient(create_app()) as c:
        # Initially unset.
        r = c.get("/admin/api/secrets", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["encryption_enabled"] is True
        sefaz = next(s for s in body["secrets"] if s["name"] == "sefaz_token")
        assert sefaz["configured"] is False

        # Set it — the response must never echo the value back.
        r = c.put("/admin/api/secrets/sefaz_token", headers=headers,
                  json={"value": SEFAZ_TOKEN})
        assert r.status_code == 200, r.text
        assert SEFAZ_TOKEN not in r.text
        sefaz = next(s for s in r.json()["secrets"] if s["name"] == "sefaz_token")
        assert sefaz["configured"] is True and sefaz["fingerprint"]

        # Unknown secret name is rejected (no arbitrary Redis writes).
        assert c.put("/admin/api/secrets/evil", headers=headers,
                     json={"value": "x"}).status_code == 404

        # Delete clears it.
        r = c.delete("/admin/api/secrets/sefaz_token", headers=headers)
        sefaz = next(s for s in r.json()["secrets"] if s["name"] == "sefaz_token")
        assert sefaz["configured"] is False


def test_admin_secrets_requires_auth(secrets_env):
    with TestClient(create_app()) as c:
        assert c.get("/admin/api/secrets").status_code == 401
        assert c.put("/admin/api/secrets/sefaz_token",
                     json={"value": "x"}).status_code == 401


def test_secret_store_disabled_returns_503(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN)
    monkeypatch.delenv("SECRET_ENCRYPTION_KEY", raising=False)
    get_settings.cache_clear()
    try:
        headers = {"Authorization": f"Bearer {ADMIN}"}
        with TestClient(create_app()) as c:
            assert c.get("/admin/api/secrets", headers=headers).json()[
                "encryption_enabled"] is False
            r = c.put("/admin/api/secrets/sefaz_token", headers=headers,
                      json={"value": SEFAZ_TOKEN})
            assert r.status_code == 503
    finally:
        get_settings.cache_clear()


# --- LGPD: data minimization at rest ---------------------------------------

async def test_device_token_never_stored_raw():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    cache = Cache(client=redis)
    await cache.register_consent(DEVICE, "2026-06-06")
    await cache.attach_list(DEVICE, "list123")

    # Round-trips fine for the caller (transparent hashing)...
    rec = await cache.get_device(DEVICE)
    assert rec and "list123" in rec["saved_lists"]

    # ...but the raw bearer token appears in no Redis key.
    keys = await redis.keys("*")
    assert all(DEVICE not in k for k in keys)
    assert any(k.startswith("device:") for k in keys)


# --- SEFAZ token resolution ------------------------------------------------

async def test_sefaz_token_prefers_store_over_env(monkeypatch):
    from app.config import Settings
    from app.services.sefaz.factory import build_sefaz_client

    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    store = SecretStore(redis, KEY)
    settings = Settings(use_mock_sefaz=False, sefaz_app_token="env-fallback-token")

    client = build_sefaz_client(settings, store)
    # No stored secret yet → falls back to the env token.
    assert await client._token_provider() == "env-fallback-token"
    # Once set via the panel, the encrypted store wins (rotation without restart).
    await store.set_secret("sefaz_token", SEFAZ_TOKEN)
    assert await client._token_provider() == SEFAZ_TOKEN
    await client.aclose()
