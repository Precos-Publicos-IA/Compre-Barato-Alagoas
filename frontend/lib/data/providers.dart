import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/config.dart';
import '../core/location.dart';
import 'api_client.dart';
import 'device_identity.dart';
import 'models.dart';

/// Shared API client.
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

/// Pseudo-anonymous device identity (token in secure storage).
final deviceIdentityProvider =
    Provider<DeviceIdentity>((ref) => DeviceIdentity());

/// Whether the user opted into saving lists on the server ("cloud sync"). This
/// is the LGPD consent toggle: enabling registers consent + a device record,
/// disabling triggers server-side erasure. The local flag is just a UI mirror.
class CloudSyncNotifier extends AsyncNotifier<bool> {
  static const _kKey = 'cloud_sync_v1';

  @override
  Future<bool> build() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getBool(_kKey) ?? false;
    } catch (_) {
      return false;
    }
  }

  Future<void> _setLocal(bool value) async {
    state = AsyncValue.data(value);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_kKey, value);
    } catch (_) {
      // Best-effort mirror; the server record is the source of truth.
    }
  }

  /// Opt in: record consent for this device on the server.
  Future<void> enable() async {
    final token = await ref.read(deviceIdentityProvider).getOrCreateToken();
    await ref.read(apiClientProvider).registerConsent(token, AppConfig.policyVersion);
    await _setLocal(true);
  }

  /// Opt out: LGPD erasure of everything stored server-side for this device.
  Future<void> disable() async {
    final token = await ref.read(deviceIdentityProvider).getOrCreateToken();
    await ref.read(apiClientProvider).deleteDevice(token);
    await _setLocal(false);
  }
}

final cloudSyncProvider =
    AsyncNotifierProvider<CloudSyncNotifier, bool>(CloudSyncNotifier.new);

/// Resolves the search origin (device location, or a Maceió default).
final locationServiceProvider =
    Provider<LocationService>((ref) => LocationService());

/// Common-item suggestion chips.
final suggestionsProvider = FutureProvider<List<Suggestion>>((ref) {
  return ref.watch(apiClientProvider).fetchSuggestions();
});

/// The user's shopping list (the basket).
class BasketNotifier extends Notifier<List<String>> {
  @override
  List<String> build() => <String>[];

  void add(String item) {
    final value = item.trim();
    if (value.isEmpty) return;
    if (state.any((e) => e.toLowerCase() == value.toLowerCase())) return;
    state = [...state, value];
  }

  void addMany(Iterable<String> items) {
    for (final i in items) {
      add(i);
    }
  }

  void removeAt(int index) {
    final copy = [...state]..removeAt(index);
    state = copy;
  }

  void clear() => state = <String>[];
}

final basketProvider =
    NotifierProvider<BasketNotifier, List<String>>(BasketNotifier.new);

/// Search controller: holds the latest results as an AsyncValue.
class SearchController extends AsyncNotifier<SearchResponse?> {
  @override
  Future<SearchResponse?> build() async => null;

  Future<void> run(List<String> items, {int? radiusKm}) async {
    if (items.isEmpty) return;
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final origin = await ref.read(locationServiceProvider).resolveOrigin();
      // Only consented (cloud-sync on) devices identify themselves, so the
      // backend saves this list to their server-side history.
      String? deviceToken;
      if (ref.read(cloudSyncProvider).asData?.value == true) {
        deviceToken = await ref.read(deviceIdentityProvider).getOrCreateToken();
      }
      return ref.read(apiClientProvider).search(
            items,
            latitude: origin.latitude,
            longitude: origin.longitude,
            radiusKm: radiusKm,
            deviceToken: deviceToken,
          );
    });
  }
}

final searchControllerProvider =
    AsyncNotifierProvider<SearchController, SearchResponse?>(SearchController.new);
