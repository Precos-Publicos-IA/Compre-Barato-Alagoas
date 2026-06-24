import 'package:compre_barato_alagoas/data/recent_lists.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// In-memory fake so the test exercises the real persistence path without
/// platform channels — and proves recent lists go through secure storage (#385).
class _MemorySecureStorage extends FlutterSecureStorage {
  final Map<String, String> data = {};

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      data[key];

  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      data.remove(key);
    } else {
      data[key] = value;
    }
  }
}

void main() {
  test('recent lists persist to secure storage, newest first, capped (#385)',
      () async {
    final storage = _MemorySecureStorage();
    final c = ProviderContainer(overrides: [
      recentListsStorageProvider.overrideWithValue(storage),
    ]);
    addTearDown(c.dispose);

    final notifier = c.read(recentListsProvider.notifier);
    await c.read(recentListsProvider.future);

    for (var i = 0; i < 7; i++) {
      await notifier.record(['item $i']);
    }

    final lists = c.read(recentListsProvider).asData!.value;
    expect(lists.length, 5); // capped at _kMax
    expect(lists.first, ['item 6']); // most recent first
    // Persisted into the (encrypted) secure store, not plaintext prefs.
    expect(storage.data.keys, contains('recent_lists_v2'));
  });
}
