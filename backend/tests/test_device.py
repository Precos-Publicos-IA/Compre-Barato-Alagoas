"""Device API: pseudo-anonymous consent, saved-list association and LGPD erasure."""

from fastapi.testclient import TestClient

from app.main import create_app

# A well-formed (hex, 32–128 chars) device token.
TOKEN = "a" * 64
HEADERS = {"X-Device-Token": TOKEN}
POLICY = "2026-06-05"


def _client() -> TestClient:
    return TestClient(create_app())


def test_device_requires_token():
    with _client() as c:
        assert c.get("/api/v1/device/me").status_code == 401
        # Malformed tokens are rejected too.
        assert (
            c.get("/api/v1/device/me", headers={"X-Device-Token": "short"}).status_code
            == 401
        )


def test_unknown_device_is_empty():
    with _client() as c:
        body = c.get("/api/v1/device/me", headers=HEADERS).json()
        assert body == {
            "known": False,
            "consented": False,
            "consent_at": None,
            "policy_version": None,
            "saved_lists": [],
        }


def test_consent_then_me_reflects_it():
    with _client() as c:
        r = c.post(
            "/api/v1/device/consent",
            headers=HEADERS,
            json={"accepted": True, "policy_version": POLICY},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["known"] and body["consented"]
        assert body["policy_version"] == POLICY
        assert body["consent_at"]

        me = c.get("/api/v1/device/me", headers=HEADERS).json()
        assert me["consented"] and me["policy_version"] == POLICY


def test_consent_must_be_accepted():
    with _client() as c:
        r = c.post(
            "/api/v1/device/consent",
            headers=HEADERS,
            json={"accepted": False, "policy_version": POLICY},
        )
        assert r.status_code == 400


def test_search_with_consented_device_saves_list_then_erasure_wipes_it():
    with _client() as c:
        c.post(
            "/api/v1/device/consent",
            headers=HEADERS,
            json={"accepted": True, "policy_version": POLICY},
        )
        search = c.post(
            "/api/v1/search", headers=HEADERS, json={"items": ["arroz", "leite"]}
        ).json()
        list_id = search["list_id"]
        assert list_id

        me = c.get("/api/v1/device/me", headers=HEADERS).json()
        assert list_id in me["saved_lists"]

        # LGPD erasure removes the device record entirely.
        deleted = c.delete("/api/v1/device/me", headers=HEADERS).json()
        assert deleted == {"deleted": True}
        after = c.get("/api/v1/device/me", headers=HEADERS).json()
        assert after["known"] is False and after["saved_lists"] == []


def test_search_without_consent_does_not_store():
    with _client() as c:
        # Token present but device never consented → nothing stored server-side.
        c.post("/api/v1/search", headers=HEADERS, json={"items": ["feijao"]})
        me = c.get("/api/v1/device/me", headers=HEADERS).json()
        assert me["known"] is False
