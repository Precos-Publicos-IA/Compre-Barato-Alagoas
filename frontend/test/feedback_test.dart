import 'package:compre_barato_alagoas/core/location.dart';
import 'package:compre_barato_alagoas/data/api_client.dart';
import 'package:compre_barato_alagoas/data/models.dart';
import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:compre_barato_alagoas/features/search/search_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _FakeLocation extends LocationService {
  @override
  Future<SearchOrigin> resolveOrigin() async => kMaceioDefault;
}

class _FakeApi extends ApiClient {
  _FakeApi({this.feedbackSucceeds = true}) : super(baseUrl: 'http://test.local');

  /// When false, simulates network/API failure from shipped [ApiClient.submitFeedback].
  final bool feedbackSucceeds;
  final List<Map<String, dynamic>> feedback = [];

  @override
  Future<List<Suggestion>> fetchSuggestions() async =>
      const [Suggestion(label: 'Arroz', emoji: '🍚')];

  @override
  Future<SearchResponse> search(
    List<String> items, {
    double? latitude,
    double? longitude,
    int? radiusKm,
    int? days,
    String? deviceToken,
    String? analyticsId,
    List<String> excludedCnpjs = const [],
  }) async {
    return SearchResponse(
      originLat: -9.65,
      originLon: -35.71,
      radiusKm: 8,
      days: 7,
      itemsRequested: items.length,
      dataSource: 'mock',
      listId: 'abc123',
      stores: [
        StoreResult(
          cnpj: '1',
          name: 'Mercado Teste',
          latitude: -9.65,
          longitude: -35.71,
          bairro: 'Centro',
          distanceKm: 1.0,
          itemsFound: items.length,
          itemsTotal: items.length,
          total: 12.34,
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
        ),
      ],
      metrics: const SearchMetrics(
        itemsRequested: 1,
        storesFound: 1,
        matchRate: 1.0,
        quantityParseRate: 1.0,
      ),
    );
  }

  @override
  Future<bool> submitFeedback({
    required String kind,
    bool? helpful,
    String? item,
    String? note,
    String? listId,
    String? deviceToken,
  }) async {
    feedback.add({'kind': kind, 'helpful': helpful, 'list_id': listId});
    return feedbackSucceeds;
  }
}

Future<void> _openResultsWithFeedback(WidgetTester tester, _FakeApi api) async {
  await tester.pumpWidget(ProviderScope(
    overrides: [
      apiClientProvider.overrideWithValue(api),
      locationServiceProvider.overrideWithValue(_FakeLocation()),
    ],
    child: const MaterialApp(home: SearchScreen()),
  ));
  await tester.pumpAndSettle();

  await tester.tap(find.textContaining('Arroz').first);
  await tester.pumpAndSettle();
  await tester.tap(find.text('VER PREÇOS'));
  await tester.pumpAndSettle();

  await tester.scrollUntilVisible(
    find.text('Este resultado foi útil?'),
    300,
    scrollable: find.byType(Scrollable).first,
  );
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('thumbs-up sends feedback and thanks the user', (tester) async {
    final api = _FakeApi();
    await tester.pumpWidget(ProviderScope(
      overrides: [
        apiClientProvider.overrideWithValue(api),
        locationServiceProvider.overrideWithValue(_FakeLocation()),
      ],
      child: const MaterialApp(home: SearchScreen()),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.textContaining('Arroz').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('VER PREÇOS'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('Este resultado foi útil?'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Sim'));
    await tester.pumpAndSettle();

    expect(api.feedback, hasLength(1));
    expect(api.feedback.first['kind'], 'helpful');
    expect(api.feedback.first['helpful'], true);
    expect(api.feedback.first['list_id'], 'abc123');
    expect(find.text('Obrigado pelo feedback!'), findsOneWidget);
  });
}
