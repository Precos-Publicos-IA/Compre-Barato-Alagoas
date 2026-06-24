import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Default secure-storage options used when the caller does not inject storage.
///
/// - **Android**: [AndroidOptions.encryptedSharedPreferences] so the bearer
///   device token is not stored in plain SharedPreferences on modern APIs
///   (issue #331). Still device-local; not a substitute for accounts.
/// - **iOS**: Keychain with [KeychainAccessibility.first_unlock_this_device] so
///   the pseudo-anonymous bearer token is available after first unlock on this
///   device only (not backed up / not portable across restores — matches the
///   "lose device → lose identity" product trade-off).
///
/// Exposed so tests can assert the shipped configuration without going through
/// platform channels.
FlutterSecureStorage createDefaultSecureStorage() => const FlutterSecureStorage(
      aOptions: AndroidOptions(
        encryptedSharedPreferences: true,
      ),
      iOptions: IOSOptions(
        accessibility: KeychainAccessibility.first_unlock_this_device,
      ),
    );

/// Pseudo-anonymous device identity — the login-free way the app gets a stable
/// server-side identity.
///
/// On first use the device mints a 256-bit random token and keeps it in secure
/// storage (Android Keystore / iOS Keychain). It's a bearer credential, so it
/// must never live in plain `shared_preferences`. By design there is **no
/// portability**: lose/reset the device → lose the token → lose the server-side
/// data. That's the accepted trade-off for not having accounts.
class DeviceIdentity {
  DeviceIdentity({FlutterSecureStorage? storage})
      : _storage = storage ?? createDefaultSecureStorage();

  static const _key = 'device_token_v1';
  final FlutterSecureStorage _storage;
  String? _cached;

  /// Returns the device token, generating and persisting one on first call.
  Future<String> getOrCreateToken() async {
    if (_cached != null) return _cached!;
    final existing = await _storage.read(key: _key);
    if (existing != null && existing.isNotEmpty) {
      return _cached = existing;
    }
    final token = _generateToken();
    await _storage.write(key: _key, value: token);
    return _cached = token;
  }

  /// 256 bits of CSPRNG entropy as lowercase hex (64 chars) — matches the
  /// backend's accepted token format.
  static String _generateToken() {
    final rng = Random.secure();
    final bytes = List<int>.generate(32, (_) => rng.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
