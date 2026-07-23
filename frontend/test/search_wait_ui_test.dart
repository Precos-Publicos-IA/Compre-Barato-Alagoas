import 'package:compre_barato_alagoas/core/location.dart';
import 'package:compre_barato_alagoas/data/api_client.dart';
import 'package:compre_barato_alagoas/data/models.dart';
import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:compre_barato_alagoas/features/results/results_screen.dart';
import 'package:compre_barato_alagoas/features/results/search_wait_copy.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class FakeLocationService extends LocationService {
  @override
  Future<SearchOrigin> resolveOrigin() async => kMaceioDefault;
}

/// Search that stays open long enough for the wait UI + phrase rotation.
class SlowFakeApiClient extends ApiClient {
  SlowFakeApiClient() : super(baseUrl: 'http://test.local');

  @override
  Future<List<Suggestion>> fetchSuggestions() async => const [];

  @override
  Future<SearchResponse> searchStream(
    List<String> items, {
    double? latitude,
    double? longitude,
    int? radiusKm,
    int? days,
    String? deviceToken,
    String? analyticsId,
    List<String> excludedCnpjs = const [],
    List<String> favoriteCnpjs = const [],
    void Function(String message)? onStatus,
    void Function(SearchResponse partial)? onPartial,
  }) async {
    onStatus?.call('Buscando preços (0/${items.length})…');
    await Future<void>.delayed(const Duration(milliseconds: 4500));
    return SearchResponse(
      originLat: -9.65,
      originLon: -35.71,
      radiusKm: 8,
      days: 7,
      itemsRequested: items.length,
      dataSource: 'mock',
      stores: [
        StoreResult(
          cnpj: '1',
          name: 'Mercado Lento',
          latitude: -9.65,
          longitude: -35.71,
          bairro: 'Centro',
          distanceKm: 1,
          itemsFound: items.length,
          itemsTotal: items.length,
          total: 10,
          items: [
            for (final it in items)
              ItemOffer(
                query: it,
                found: true,
                description: it.toUpperCase(),
                price: 5,
                unitPrice: 5,
                baseUnit: 'un',
                quantity: 1,
                unit: 'un',
                quantityParsed: true,
              ),
          ],
          missing: const [],
        ),
      ],
      metrics: SearchMetrics(
        itemsRequested: items.length,
        storesFound: 1,
        matchRate: 1,
        quantityParseRate: 1,
      ),
    );
  }
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('loading screen shows ETA, notify promise, and rotates phrases',
      (tester) async {
    final container = ProviderContainer(
      overrides: [
        apiClientProvider.overrideWithValue(SlowFakeApiClient()),
        locationServiceProvider.overrideWithValue(FakeLocationService()),
      ],
    );
    addTearDown(container.dispose);

    container.read(basketProvider.notifier).add('arroz');

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: ResultsScreen()),
      ),
    );

    // Kick off search (same path as VER PREÇOS).
    // ignore: unawaited_futures
    container.read(searchControllerProvider.notifier).run(const ['arroz']);
    await tester.pump(); // start async
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.textContaining('Tempo estimado'), findsWidgets);
    expect(find.textContaining('5 min'), findsWidgets);
    // Copy promises a completion ping (permission-granted) or how to enable it.
    expect(find.textContaining('notifica'), findsWidgets);
    expect(find.textContaining('NFC-e'), findsOneWidget);

    // First rotating phrase is on screen.
    expect(find.text(kSearchWaitPhrases.first), findsOneWidget);

    // Advance the phrase timer.
    await tester.pump(kSearchWaitPhrasePeriod + const Duration(milliseconds: 50));
    expect(find.text(kSearchWaitPhrases[1]), findsOneWidget);

    // Finish the slow search so timers/cleanup settle.
    await tester.pump(const Duration(seconds: 5));
    await tester.pumpAndSettle();
    expect(find.text('Mercado Lento'), findsOneWidget);
  });
}
