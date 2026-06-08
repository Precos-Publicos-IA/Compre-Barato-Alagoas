import 'dart:math';

import 'package:shared_preferences/shared_preferences.dart';

/// Anonymous usage-measurement id (LGPD legal basis: legítimo interesse, opt-out).
///
/// Deliberately **separate** from [DeviceIdentity] and **not** a credential: it is a
/// random, non-PII value used only so the backend can count unique devices *in
/// aggregate* (a salted hash of it enters a HyperLogLog — never linked to your lists
/// or identity, never reversible). Because it isn't a secret, it lives in plain
/// `shared_preferences` and can be rotated/cleared at any time (e.g. when the user
/// turns off "Estatísticas anônimas de uso").
class AnalyticsId {
  AnalyticsId();

  static const _key = 'analytics_id_v1';
  String? _cached;

  /// Returns the id, generating and persisting one on first call.
  ///
  /// Resilient by design: this id is a convenience for *aggregate* counting, never
  /// essential. If device storage is unavailable (e.g. `shared_preferences` isn't
  /// registered on the web target) it falls back to a volatile in-memory id and
  /// never throws — a non-critical analytics read must not abort the core search.
  Future<String> getOrCreate() async {
    if (_cached != null) return _cached!;
    try {
      final prefs = await SharedPreferences.getInstance();
      final existing = prefs.getString(_key);
      if (existing != null && existing.isNotEmpty) return _cached = existing;
      final id = _generate();
      await prefs.setString(_key, id);
      return _cached = id;
    } catch (_) {
      return _cached ??= _generate();
    }
  }

  /// Forget the id (opt-out / erasure). A future opt-in mints a fresh one, so past
  /// aggregate counts can't be tied to future activity. Best-effort.
  Future<void> clear() async {
    _cached = null;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_key);
    } catch (_) {
      // Best-effort; an orphaned local id is harmless (it's anonymous).
    }
  }

  /// 160 bits of CSPRNG entropy as lowercase hex (40 chars) — within the backend's
  /// accepted token shape (32–128 hex chars).
  static String _generate() {
    final rng = Random.secure();
    final bytes = List<int>.generate(20, (_) => rng.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
