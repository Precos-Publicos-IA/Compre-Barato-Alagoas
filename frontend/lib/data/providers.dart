import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/location.dart';
import 'api_client.dart';
import 'models.dart';

/// Shared API client.
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

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
      return ref.read(apiClientProvider).search(
            items,
            latitude: origin.latitude,
            longitude: origin.longitude,
            radiusKm: radiusKm,
          );
    });
  }
}

final searchControllerProvider =
    AsyncNotifierProvider<SearchController, SearchResponse?>(SearchController.new);
