import 'package:compre_barato_alagoas/core/location.dart';
import 'package:compre_barato_alagoas/data/api_client.dart';
import 'package:compre_barato_alagoas/data/models.dart';
import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:compre_barato_alagoas/features/search/search_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Deterministic location so tests don't touch the GPS plugin.
class FakeLocationService extends LocationService {
  @override
  Future<SearchOrigin> resolveOrigin() async => kMaceioDefault;
}

/// In-memory fake so widget tests never touch the network.
class FakeApiClient extends ApiClient {
  FakeApiClient() : super(baseUrl: 'http://test.local');

  @override
  Future<List<Suggestion>> fetchSuggestions() async => const [
        Suggestion(label: 'Arroz', emoji: '🍚'),
        Suggestion(label: 'Leite', emoji: '🥛'),
      ];

  @override
  Future<SearchResponse> search(
    List<String> items, {
    double? latitude,
    double? longitude,
    int? radiusKm,
    int? days,
    String? deviceToken,
  }) async {
    StoreResult store(String cnpj, String name, double total) => StoreResult(
          cnpj: cnpj,
          name: name,
          latitude: -9.65,
          longitude: -35.71,
          bairro: 'Centro',
          distanceKm: 1.0,
          itemsFound: items.length,
          itemsTotal: items.length,
          total: total,
          items: [
            for (final it in items)
              ItemOffer(
                query: it,
                found: true,
                description: it.toUpperCase(),
                price: 6.17,
                unitPrice: 6.17,
                baseUnit: 'kg',
                quantity: 1,
                unit: 'kg',
                quantityParsed: true,
              ),
          ],
          missing: const [],
        );
    return SearchResponse(
      originLat: -9.65,
      originLon: -35.71,
      radiusKm: 8,
      days: 7,
      itemsRequested: items.length,
      dataSource: 'mock',
      stores: [
        store('1', 'Mercado Teste', 12.34),
        store('2', 'Mercado Dois', 15.00),
      ],
      metrics: const SearchMetrics(
        itemsRequested: 1,
        storesFound: 2,
        matchRate: 1.0,
        quantityParseRate: 1.0,
      ),
    );
  }
}

Widget _app() => ProviderScope(
      overrides: [
        apiClientProvider.overrideWithValue(FakeApiClient()),
        locationServiceProvider.overrideWithValue(FakeLocationService()),
      ],
      child: const MaterialApp(home: SearchScreen()),
    );

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('renders core search UI', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.text('VER PREÇOS'), findsOneWidget);
    expect(find.byIcon(Icons.mic), findsOneWidget);
    // Suggestion chips from the fake.
    expect(find.textContaining('Arroz'), findsWidgets);
  });

  testWidgets('tapping a suggestion adds it to the basket', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('Arroz').first);
    await tester.pumpAndSettle();

    // The basket section header shows a count, and the item is listed.
    expect(find.text('Sua lista (1)'), findsOneWidget);
  });

  testWidgets('searching navigates to results with a store', (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('Leite').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('VER PREÇOS'));
    await tester.pumpAndSettle();

    expect(find.text('Mercado Teste'), findsOneWidget);
    expect(find.text('EDITAR LISTA'), findsOneWidget);
  });

  testWidgets('results list shows both stores and the savings banner',
      (tester) async {
    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('Arroz').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('VER PREÇOS'));
    await tester.pumpAndSettle();

    // Best store + savings banner at the top.
    expect(find.text('Mercado Teste'), findsOneWidget);
    expect(find.textContaining('economizar'), findsOneWidget);
    expect(find.text('R\$ 2,66'), findsOneWidget); // 15.00 - 12.34
    expect(find.text('MAIS BARATO'), findsOneWidget);

    // The second store is in the same vertical list (scroll to reach it).
    await tester.scrollUntilVisible(
      find.text('Mercado Dois'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Mercado Dois'), findsOneWidget);
  });
}
