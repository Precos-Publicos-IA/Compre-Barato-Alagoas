import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _kKey = 'recent_lists_v1';
const _kMax = 5;

/// The user's recently searched shopping lists, persisted on the device so they
/// can be reused without retyping. Resilient: any storage failure yields [].
class RecentLists extends AsyncNotifier<List<List<String>>> {
  @override
  Future<List<List<String>>> build() => _load();

  Future<List<List<String>>> _load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_kKey);
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
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_kKey, jsonEncode(lists));
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
