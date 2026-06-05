import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Pseudo-anonymous device identity — the login-free way the app gets a stable
/// server-side identity.
///
/// On first use the device mints a 256-bit random token and keeps it in secure
/// storage (Android Keystore-backed). It's a bearer credential, so it must never
/// live in plain `shared_preferences`. By design there is **no portability**:
/// lose/reset the device → lose the token → lose the server-side data. That's the
/// accepted trade-off for not having accounts.
class DeviceIdentity {
  DeviceIdentity({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

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
