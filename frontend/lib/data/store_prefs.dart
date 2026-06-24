import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// A set of stores the user marked, kept as `{cnpj: nomeFantasia}` so the
/// management screen can show names without a live search. Used for both
/// **favoritas** and **ocultas** stores.
///
/// Stays only on the device (`shared_preferences`). The only thing that ever
/// leaves is the list of hidden CNPJs, which rides along with a search request as
/// an ephemeral server-side filter — it is never stored server-side. Load failures
/// yield `{}`; **write** failures throw [PrefsWriteException] so UI can surface
/// them (same class of issue as CloudSync #399 / #408).
class StorePrefs extends AsyncNotifier<Map<String, String>> {
  StorePrefs(this._key);

  final String _key;

  @override
  Future<Map<String, String>> build() => _load();

  Future<Map<String, String>> _load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_key);
      if (raw == null) return {};
      final decoded = jsonDecode(raw) as Map<String, dynamic>;
      return decoded.map((k, v) => MapEntry(k, v as String));
    } catch (_) {
      return {};
    }
  }

  /// Writes then updates in-memory state only on success (#408).
  Future<void> _persist(Map<String, String> value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final ok = await prefs.setString(_key, jsonEncode(value));
      if (!ok) throw const PrefsWriteException();
    } on PrefsWriteException {
      rethrow;
    } catch (_) {
      throw const PrefsWriteException();
    }
    state = AsyncValue.data(value);
  }

  Future<void> add(String cnpj, String name) async {
    final current = state.asData?.value ?? await _load();
    if (current[cnpj] == name) return;
    final next = Map<String, String>.from(current);
    next[cnpj] = name;
    await _persist(next);
  }

  Future<void> remove(String cnpj) async {
    final current = state.asData?.value ?? await _load();
    if (!current.containsKey(cnpj)) return;
    final next = Map<String, String>.from(current);
    next.remove(cnpj);
    await _persist(next);
  }
}

/// Local SharedPreferences write failed (#408).
class PrefsWriteException implements Exception {
  const PrefsWriteException();

  @override
  String toString() => 'PrefsWriteException';
}
