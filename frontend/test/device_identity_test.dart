import 'package:compre_barato_alagoas/data/device_identity.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

/// In-memory fake — avoids platform channels while exercising the real
/// [DeviceIdentity.getOrCreateToken] path (mint, cache, reuse).
class _MemorySecureStorage extends FlutterSecureStorage {
  _MemorySecureStorage() : super();

  final Map<String, String> _data = {};

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
      _data[key];

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
      _data.remove(key);
    } else {
      _data[key] = value;
    }
  }

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _data.remove(key);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('createDefaultSecureStorage sets iOS Keychain accessibility', () {
    final storage = createDefaultSecureStorage();
    expect(
      storage.iOptions.accessibility,
      KeychainAccessibility.first_unlock_this_device,
    );
  });

  test('getOrCreateToken mints a 64-char hex token and reuses it', () async {
    final id = DeviceIdentity(storage: _MemorySecureStorage());
    final first = await id.getOrCreateToken();
    expect(first, matches(RegExp(r'^[0-9a-f]{64}$')));
    expect(await id.getOrCreateToken(), equals(first));
  });

  test('getOrCreateToken returns existing storage value without reminting',
      () async {
    final mem = _MemorySecureStorage();
    await mem.write(
      key: 'device_token_v1',
      value: 'a' * 64,
    );
    final id = DeviceIdentity(storage: mem);
    expect(await id.getOrCreateToken(), equals('a' * 64));
  });

  test('clear removes token; next getOrCreateToken mints a different one',
      () async {
    final mem = _MemorySecureStorage();
    final id = DeviceIdentity(storage: mem);
    final first = await id.getOrCreateToken();
    await id.clear();
    final second = await id.getOrCreateToken();
    expect(second, matches(RegExp(r'^[0-9a-f]{64}$')));
    expect(second, isNot(equals(first)));
  });
}
