import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/config.dart';
import '../core/location.dart';
import 'analytics_id.dart';
import 'api_client.dart';
import 'device_identity.dart';
import 'models.dart';
import 'store_prefs.dart';

/// Shared API client.
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

/// Pseudo-anonymous device identity (token in secure storage).
final deviceIdentityProvider =
    Provider<DeviceIdentity>((ref) => DeviceIdentity());

/// Anonymous usage-measurement id (separate from the credential above).
final analyticsIdProvider = Provider<AnalyticsId>((ref) => AnalyticsId());

/// Whether anonymous usage statistics are sent. Legal basis: legítimo interesse
/// (LGPD); this is the Art. 18 §2 opt-out, so it defaults ON. Turning it off stops
/// the id being sent and forgets it locally.
class UsageStatsNotifier extends AsyncNotifier<bool> {
  static const _kKey = 'usage_stats_v1';

  @override
  Future<bool> build() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getBool(_kKey) ?? true;
    } catch (_) {
      return true;
    }
  }

  Future<void> set(bool value) async {
    state = AsyncValue.data(value);
    if (!value) {
      await ref.read(analyticsIdProvider).clear();
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_kKey, value);
    } catch (_) {
      // Best-effort mirror.
    }
  }
}

final usageStatsProvider =
    AsyncNotifierProvider<UsageStatsNotifier, bool>(UsageStatsNotifier.new);

/// User-tunable search parameters (radius + recency window), kept on-device and
/// applied to every search. Defaults mirror the backend (8 km / 7 days). Bounds
/// match the SEFAZ limits enforced server-side (radius 1..15, days 1..10).
class SearchPrefs {
  const SearchPrefs({this.radiusKm = 8, this.days = 7});
  final int radiusKm;
  final int days;

  SearchPrefs copyWith({int? radiusKm, int? days}) =>
      SearchPrefs(radiusKm: radiusKm ?? this.radiusKm, days: days ?? this.days);
}

class SearchPrefsNotifier extends AsyncNotifier<SearchPrefs> {
  static const _kRadius = 'search_radius_km_v1';
  static const _kDays = 'search_days_v1';
  static const defaultRadius = 8;
  static const defaultDays = 7;

  @override
  Future<SearchPrefs> build() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return SearchPrefs(
        radiusKm: prefs.getInt(_kRadius) ?? defaultRadius,
        days: prefs.getInt(_kDays) ?? defaultDays,
      );
    } catch (_) {
      return const SearchPrefs();
    }
  }

  Future<void> _persist(SearchPrefs value) async {
    state = AsyncValue.data(value);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(_kRadius, value.radiusKm);
      await prefs.setInt(_kDays, value.days);
    } catch (_) {
      // Best-effort mirror.
    }
  }

  Future<void> setRadius(int km) async {
    final cur = state.asData?.value ?? const SearchPrefs();
    await _persist(cur.copyWith(radiusKm: km.clamp(1, 15)));
  }

  Future<void> setDays(int days) async {
    final cur = state.asData?.value ?? const SearchPrefs();
    await _persist(cur.copyWith(days: days.clamp(1, 10)));
  }

  Future<void> reset() =>
      _persist(const SearchPrefs(radiusKm: defaultRadius, days: defaultDays));
}

final searchPrefsProvider =
    AsyncNotifierProvider<SearchPrefsNotifier, SearchPrefs>(
        SearchPrefsNotifier.new);

/// Stores the user marked as favourites / hidden ("ocultas"), kept on-device.
final favoriteStoresProvider =
    AsyncNotifierProvider<StorePrefs, Map<String, String>>(
        () => StorePrefs('favorite_stores_v1'));
final avoidedStoresProvider =
    AsyncNotifierProvider<StorePrefs, Map<String, String>>(
        () => StorePrefs('avoided_stores_v1'));

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

  /// Persists the local consent mirror. Throws [CloudSyncLocalMirrorException]
  /// if prefs cannot be written so callers do not claim success (#399).
  Future<void> _setLocal(bool value) async {
    state = AsyncValue.data(value);
    try {
      final prefs = await SharedPreferences.getInstance();
      final ok = await prefs.setBool(_kKey, value);
      if (!ok) {
        throw const CloudSyncLocalMirrorException();
      }
    } on CloudSyncLocalMirrorException {
      rethrow;
    } catch (_) {
      throw const CloudSyncLocalMirrorException();
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

/// Local prefs write failed after a successful server consent/erase step (#399).
class CloudSyncLocalMirrorException implements Exception {
  const CloudSyncLocalMirrorException();

  @override
  String toString() => 'CloudSyncLocalMirrorException';
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

  Future<void> run(List<String> items, {int? radiusKm, int? days}) async {
    if (items.isEmpty) return;
    state = const AsyncValue.loading();
    final result = await AsyncValue.guard(() async {
      final origin = await ref.read(locationServiceProvider).resolveOrigin();
      // User-tuned search params (Configurações); fall back to backend defaults.
      final prefs = ref.read(searchPrefsProvider).asData?.value;
      final effRadius = radiusKm ?? prefs?.radiusKm;
      final effDays = days ?? prefs?.days;
      // Only consented (cloud-sync on) devices identify themselves, so the
      // backend saves this list to their server-side history.
      String? deviceToken;
      if (ref.read(cloudSyncProvider).asData?.value == true) {
        deviceToken = await ref.read(deviceIdentityProvider).getOrCreateToken();
      }
      // Anonymous usage measurement (opt-out): sent on every search unless off.
      String? analyticsId;
      if (ref.read(usageStatsProvider).asData?.value ?? true) {
        analyticsId = await ref.read(analyticsIdProvider).getOrCreate();
      }
      final avoided = ref.read(avoidedStoresProvider).asData?.value ?? const {};
      return ref.read(apiClientProvider).search(
            items,
            latitude: origin.latitude,
            longitude: origin.longitude,
            radiusKm: effRadius,
            days: effDays,
            deviceToken: deviceToken,
            analyticsId: analyticsId,
            excludedCnpjs: avoided.keys.toList(),
          );
    });
    // The search can outlive the provider (user navigated away, or the test
    // ended). Don't write state into a disposed notifier.
    if (ref.mounted) {
      state = result;
    }
  }
}

final searchControllerProvider =
    AsyncNotifierProvider<SearchController, SearchResponse?>(SearchController.new);
