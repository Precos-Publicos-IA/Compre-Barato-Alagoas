import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/config.dart';
import '../core/location.dart';
import 'analytics_id.dart';
import 'api_client.dart';
import 'device_identity.dart';
import 'models.dart';
import 'search_notifications.dart';
import 'search_wait_session.dart';
import 'store_prefs.dart';

export 'search_wait_session.dart';

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

/// Offline staple list so home never looks empty if the network is slow/down.
const kFallbackSuggestions = <Suggestion>[
  Suggestion(label: 'Arroz', emoji: '🍚'),
  Suggestion(label: 'Feijão', emoji: '🫘'),
  Suggestion(label: 'Leite', emoji: '🥛'),
  Suggestion(label: 'Ovo', emoji: '🥚'),
  Suggestion(label: 'Açúcar', emoji: '🧂'),
  Suggestion(label: 'Café', emoji: '☕'),
  Suggestion(label: 'Óleo', emoji: '🛢️'),
  Suggestion(label: 'Macarrão', emoji: '🍝'),
  Suggestion(label: 'Banana', emoji: '🍌'),
  Suggestion(label: 'Tomate', emoji: '🍅'),
  Suggestion(label: 'Frango', emoji: '🍗'),
  Suggestion(label: 'Refrigerante', emoji: '🥤'),
];

/// Common-item suggestion chips (network with offline fallback).
final suggestionsProvider = FutureProvider<List<Suggestion>>((ref) async {
  try {
    final items = await ref.watch(apiClientProvider).fetchSuggestions();
    if (items.isNotEmpty) return items;
  } catch (_) {
    // Fall through to offline staples.
  }
  return kFallbackSuggestions;
});

/// The user's shopping list (the basket).
/// Max basket size. Mirrors the backend SearchRequest cap (items max_length=30):
/// enforcing it client-side avoids an opaque 422 when a share link or recent list
/// would push the basket over the limit (#340).
const int kMaxBasketItems = 30;

class BasketNotifier extends Notifier<List<String>> {
  @override
  List<String> build() => <String>[];

  /// Adds an item. No-op when empty, a case-insensitive duplicate (#409), or when
  /// the basket is already full (#340).
  void add(String item) {
    final value = item.trim();
    if (value.isEmpty) return;
    if (state.length >= kMaxBasketItems) return;
    if (state.any((e) => e.toLowerCase() == value.toLowerCase())) return;
    state = [...state, value];
  }

  void addMany(Iterable<String> items) {
    for (final i in items) {
      if (state.length >= kMaxBasketItems) break;
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

/// Live status line while a progressive search is running (PT, user-facing).
class SearchStatusNotifier extends Notifier<String?> {
  @override
  String? build() => null;

  void set(String? value) => state = value;
}

final searchStatusProvider =
    NotifierProvider<SearchStatusNotifier, String?>(SearchStatusNotifier.new);

/// True while a search stream is still open (partial results may already show).
class SearchBusyNotifier extends Notifier<bool> {
  @override
  bool build() => false;

  void set(bool value) => state = value;
}

final searchBusyProvider =
    NotifierProvider<SearchBusyNotifier, bool>(SearchBusyNotifier.new);

/// Search controller: holds the latest results as an AsyncValue.
class SearchController extends AsyncNotifier<SearchResponse?> {
  // Monotonic id for the latest run. A slower earlier search must not overwrite the
  // results of a newer one that the user kicked off in the meantime (#337).
  int _runGeneration = 0;

  @override
  Future<SearchResponse?> build() async => null;

  Future<void> run(List<String> items, {int? radiusKm, int? days}) async {
    if (items.isEmpty) return;
    final generation = ++_runGeneration;
    state = const AsyncValue.loading();
    ref.read(searchBusyProvider.notifier).set(true);
    ref.read(searchStatusProvider.notifier).set('Iniciando busca…');

    // Ask for notification permission early so the wait screen can promise a
    // completion ping (long SEFAZ/web gathers often take minutes).
    final canNotify = await SearchNotifications.instance.ensurePermission();
    if (ref.mounted && generation == _runGeneration) {
      ref.read(searchWaitSessionProvider.notifier).begin(
            items.length,
            notifyPromise: canNotify,
          );
    }

    final runStarted = DateTime.now();
    SearchResponse? finalResult;

    try {
      final origin = await ref.read(locationServiceProvider).resolveOrigin();
      final prefs = ref.read(searchPrefsProvider).asData?.value;
      final effRadius = radiusKm ?? prefs?.radiusKm;
      final effDays = days ?? prefs?.days;
      String? deviceToken;
      if (ref.read(cloudSyncProvider).asData?.value == true) {
        deviceToken = await ref.read(deviceIdentityProvider).getOrCreateToken();
      }
      String? analyticsId;
      if (ref.read(usageStatsProvider).asData?.value ?? true) {
        analyticsId = await ref.read(analyticsIdProvider).getOrCreate();
      }
      final avoided = ref.read(avoidedStoresProvider).asData?.value ?? const {};
      final favorites =
          ref.read(favoriteStoresProvider).asData?.value ?? const {};

      finalResult = await ref.read(apiClientProvider).searchStream(
            items,
            latitude: origin.latitude,
            longitude: origin.longitude,
            radiusKm: effRadius,
            days: effDays,
            deviceToken: deviceToken,
            analyticsId: analyticsId,
            excludedCnpjs: avoided.keys.toList(),
            favoriteCnpjs: favorites.keys.toList(),
            onStatus: (msg) {
              if (ref.mounted && generation == _runGeneration) {
                ref.read(searchStatusProvider.notifier).set(msg);
              }
            },
            onPartial: (partial) {
              if (ref.mounted && generation == _runGeneration) {
                state = AsyncValue.data(partial);
              }
            },
          );

      if (ref.mounted && generation == _runGeneration) {
        state = AsyncValue.data(finalResult);
        ref.read(searchStatusProvider.notifier).set(null);
      }
    } catch (e, st) {
      if (ref.mounted && generation == _runGeneration) {
        // Keep partials if we already showed some stores.
        final had = state.asData?.value;
        if (had == null || had.stores.isEmpty) {
          state = AsyncValue.error(e, st);
        }
        ref.read(searchStatusProvider.notifier).set(null);
      }
    } finally {
      if (ref.mounted && generation == _runGeneration) {
        ref.read(searchBusyProvider.notifier).set(false);
        ref.read(searchWaitSessionProvider.notifier).clear();
        // Only ping when the wait was meaningful (avoids noise on warm cache /
        // unit tests with instant fakes).
        final elapsed = DateTime.now().difference(runStarted);
        final result = finalResult ?? state.asData?.value;
        if (elapsed >= const Duration(seconds: 3) && result != null) {
          // Fire-and-forget; never block the UI teardown path.
          // ignore: unawaited_futures
          SearchNotifications.instance.notifySearchDone(
            storeCount: result.stores.length,
            itemsRequested: result.itemsRequested,
          );
        }
      }
    }
  }
}

final searchControllerProvider =
    AsyncNotifierProvider<SearchController, SearchResponse?>(SearchController.new);
