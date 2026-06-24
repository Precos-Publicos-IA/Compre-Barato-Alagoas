import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'device_identity.dart' show createDefaultSecureStorage;

// v2: moved off plain shared_preferences into secure storage (#385). The old
// plaintext `recent_lists_v1` is simply abandoned (convenience data, not critical).
const _kKey = 'recent_lists_v2';
const _kMax = 5;

/// Secure storage used for recent lists. Overridable in tests with an in-memory fake.
final recentListsStorageProvider =
    Provider<FlutterSecureStorage>((ref) => createDefaultSecureStorage());

/// The user's recently searched shopping lists, persisted on the device so they
/// can be reused without retyping. Stored in secure storage (Android Keystore /
/// iOS Keychain) rather than plaintext prefs, so a shared/family device doesn't
/// leak the household's shopping history (#385). Resilient: any failure yields [].
class RecentLists extends AsyncNotifier<List<List<String>>> {
  FlutterSecureStorage get _storage => ref.read(recentListsStorageProvider);

  @override
  Future<List<List<String>>> build() => _load();

  Future<List<List<String>>> _load() async {
    try {
      final raw = await _storage.read(key: _kKey);
      if (raw == null) return [];
      final decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .map((e) => (e as List<dynamic>).map((s) => s as String).toList())
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> _persist(List<List<String>> lists) async {
    try {
      await _storage.write(key: _kKey, value: jsonEncode(lists));
    } catch (_) {
      // Best-effort; recent lists are a convenience, not critical state.
    }
  }

  /// Records a list as the most recent, de-duplicating by content (case-insensitive).
  Future<void> record(List<String> items) async {
    final clean =
        items.map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    if (clean.isEmpty) return;
    final current = state.asData?.value ?? await _load();
    bool sameList(List<String> a, List<String> b) {
      if (a.length != b.length) return false;
      for (var i = 0; i < a.length; i++) {
        if (a[i].toLowerCase() != b[i].toLowerCase()) return false;
      }
      return true;
    }

    final next = <List<String>>[
      clean,
      ...current.where((l) => !sameList(l, clean)),
    ].take(_kMax).toList();
    state = AsyncValue.data(next);
    await _persist(next);
  }

  Future<void> clear() async {
    state = const AsyncValue.data([]);
    await _persist([]);
  }
}

final recentListsProvider =
    AsyncNotifierProvider<RecentLists, List<List<String>>>(RecentLists.new);
