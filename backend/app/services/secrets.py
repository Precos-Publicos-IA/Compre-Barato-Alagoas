"""Encrypted-at-rest secret store (Redis-backed, Fernet-encrypted).

Why this exists
---------------
Third-party credentials like the SEFAZ ``AppToken`` must never live in the repo,
in ``.env``, in logs or in any API response. They are entered once through the
admin panel (over HTTPS), encrypted here and kept in Redis. The plaintext is only
ever held in memory while a request to the third party is in flight.

Honest threat model
-------------------
The backend has to send the token to SEFAZ in cleartext, so the running process
must hold the plaintext in memory. **No scheme can hide a secret from someone with
root on the same box** (they can read process memory or the decryption key). What
this *does* guarantee:

* the token is never written to disk in cleartext (Redis AOF/RDB dumps and backups
  hold only ciphertext);
* it never appears in git, ``.env``, logs or any API response (write-only;
  ``status`` returns only a short fingerprint so an operator can confirm *which*
  token is active without revealing it);
* an agent/operator doing normal work never encounters it — reading the repo,
  ``.env`` or logs yields nothing. Decrypting it is a deliberate, visible act.

The single residual secret is ``SECRET_ENCRYPTION_KEY`` (the Fernet key), which
lives in the server ``.env``. Ciphertext (Redis) and key (env) are kept in separate
stores, so neither one alone leaks the token.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Secrets an operator may manage from the admin panel. Anything outside this set
# is rejected, so the endpoint can't be used to write arbitrary Redis keys.
MANAGED_SECRETS: dict[str, str] = {
    "sefaz_token": "Token de acesso SEFAZ (AppToken)",
}

_PREFIX = "secret:"
# Truncated, salted fingerprint of the plaintext — lets an operator confirm which
# value is loaded without exposing it. Non-reversible (and the token is never shown).
_FP_SALT = "compre-barato-alagoas/secret-fingerprint/v1"


def fingerprint(value: str) -> str:
    return hashlib.sha256((_FP_SALT + value).encode()).hexdigest()[:12]


class SecretStoreUnavailable(RuntimeError):
    """Raised when a write is attempted but no encryption key is configured."""


class SecretStore:
    """Encrypts secrets with Fernet (AES-128-CBC + HMAC) and keeps them in Redis."""

    def __init__(self, redis: Any, encryption_key: str = "") -> None:
        self._redis = redis
        self._fernet = None
        if encryption_key:
            from cryptography.fernet import Fernet

            self._fernet = Fernet(encryption_key.encode())

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    async def set_secret(self, name: str, value: str) -> None:
        if self._fernet is None:
            raise SecretStoreUnavailable("SECRET_ENCRYPTION_KEY is not configured")
        ciphertext = self._fernet.encrypt(value.encode()).decode()
        await self._redis.hset(
            _PREFIX + name,
            mapping={
                "ct": ciphertext,
                "fp": fingerprint(value),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def get_secret(self, name: str) -> str | None:
        """Return the decrypted secret, or None if unset/undecryptable. Never logs the value."""
        if self._fernet is None:
            return None
        ciphertext = await self._redis.hget(_PREFIX + name, "ct")
        if not ciphertext:
            return None
        if isinstance(ciphertext, bytes):
            ciphertext = ciphertext.decode()
        from cryptography.fernet import InvalidToken

        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            # Wrong/rotated key — surface as "not configured" rather than leaking.
            logger.error("secret %r could not be decrypted (key mismatch?)", name)
            return None

    async def delete_secret(self, name: str) -> bool:
        return bool(await self._redis.delete(_PREFIX + name))

    async def status(self, name: str) -> dict[str, Any]:
        """Non-sensitive status for the admin UI: configured flag, fingerprint, timestamp."""
        rec = await self._redis.hgetall(_PREFIX + name)
        rec = {
            (k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in (rec or {}).items()
        }
        return {
            "name": name,
            "label": MANAGED_SECRETS.get(name, name),
            "configured": bool(rec.get("ct")),
            "fingerprint": rec.get("fp"),
            "updated_at": rec.get("updated_at"),
        }
