# Ops: rotating `SECRET_ENCRYPTION_KEY` (Fernet) — #282

Admin-managed secrets (for example the SEFAZ `AppToken`) are stored in Redis as
Fernet ciphertext. The envelope key is `SECRET_ENCRYPTION_KEY` in the server
`.env` (see `.env.example`). Losing it without a backup makes existing ciphertext
unreadable; the code treats decrypt failure as “secret not configured”.

## Backup (before anything else)

1. Store the current Fernet key in the same offline/operator secrets store as
   `ADMIN_TOKEN` (password manager / sealed ops channel). **Never** commit to git.
2. Confirm you can log into `admin.*` and see current secret **fingerprints**
   (values are never shown).
3. Ensure Redis AOF/backups are healthy if you rely on them for other data (#154).

## Emergency: key leaked

1. Generate a **new** Fernet key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. In admin (old key still in `.env`): **re-enter** each managed secret value
   (SEFAZ token, etc.) so they are encrypted under the old key — or note values
   from your external password store.
3. Update `.env` `SECRET_ENCRYPTION_KEY` to the new key; redeploy/restart API.
4. Immediately **PUT** each secret again via admin so ciphertext is re-wrapped
   under the new key. Old ciphertext becomes useless (good if the leak included
   Redis dumps + old key).
5. Rotate the SEFAZ token at the provider if the plaintext token may have leaked
   with the key.

## Planned rotation (minimal downtime)

Code today supports a **single** active key only (no `SECRET_ENCRYPTION_KEY_PREVIOUS`
dual-read yet). Planned procedure:

1. Schedule a short maintenance window (or accept brief SEFAZ failures).
2. Backup old key + export/re-enter secret values from operator store.
3. Deploy new `SECRET_ENCRYPTION_KEY`; restart API.
4. Re-PUT all managed secrets via admin (required — old blobs will not decrypt).
5. Verify a real search with `USE_MOCK_SEFAZ=false` succeeds.
6. Destroy old key copies after verification.

### Desired engineering follow-up (not yet implemented)

- Support `SECRET_ENCRYPTION_KEY_PREVIOUS` for decrypt-only during migration.
- Admin action “re-wrap all secrets” that decrypts with previous and encrypts with
  current in one authenticated pass.
- Metric/log when decrypt fails (wrong key vs corruption).

## Related

- `backend/app/services/secrets.py`
- Admin routes: `/admin/api/secrets`
- Issues: #146 (admin token identity), #235 (secret audit trail), #154 (backups)
