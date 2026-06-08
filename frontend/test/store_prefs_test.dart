import 'package:compre_barato_alagoas/data/api_client.dart';
import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('favorite/avoided store prefs add, persist and are mutually managed',
      () async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final favorites = container.read(favoriteStoresProvider.notifier);
    final avoided = container.read(avoidedStoresProvider.notifier);
    // Let the initial builds settle.
    await container.read(favoriteStoresProvider.future);
    await container.read(avoidedStoresProvider.future);

    await favorites.add('111', 'Mercado A');
    await avoided.add('222', 'Mercado B');

    expect(container.read(favoriteStoresProvider).value, {'111': 'Mercado A'});
    expect(container.read(avoidedStoresProvider).value, {'222': 'Mercado B'});

    // Probe: multiple entries for the *same* pref type must be retained (previously
    // all adds clobbered under the literal key "cnpj").
    await avoided.add('333', 'Mercado C');
    await avoided.add('444', 'Mercado D');
    expect(container.read(avoidedStoresProvider).value, {
      '222': 'Mercado B',
      '333': 'Mercado C',
      '444': 'Mercado D',
    });

    // Clean probe additions so the subsequent persisted-container assertions
    // still see the originally expected single entry for avoided.
    await avoided.remove('333');
    await avoided.remove('444');

    // Persisted to shared_preferences (survives a fresh container).
    final container2 = ProviderContainer();
    addTearDown(container2.dispose);
    expect(await container2.read(favoriteStoresProvider.future),
        {'111': 'Mercado A'});
    expect(await container2.read(avoidedStoresProvider.future),
        {'222': 'Mercado B'});

    await favorites.remove('111');
    expect(container.read(favoriteStoresProvider).value, isEmpty);
  });

  test('search sends X-Analytics-Id and excluded_cnpjs only when provided',
      () async {
    final captured = <http.Request>[];
    final client = MockClient((req) async {
      captured.add(req);
      return http.Response(
        '{"origin":{"latitude":0,"longitude":0},"radius_km":8,"days":7,'
        '"items_requested":1,"data_source":"mock","stores":[],'
        '"metrics":{"items_requested":1,"stores_found":0,"match_rate":0,'
        '"quantity_parse_rate":0}}',
        200,
      );
    });
    final api = ApiClient(client: client, baseUrl: 'http://test.local');

    // With an id + excluded list: header present, body carries CNPJs.
    await api.search(['arroz'],
        analyticsId: 'deadbeef', excludedCnpjs: ['999']);
    expect(captured.last.headers[ApiClient.analyticsIdHeader], 'deadbeef');
    expect(captured.last.body, contains('excluded_cnpjs'));
    expect(captured.last.body, contains('999'));

    // Opted out (no id, no exclusions): neither is sent.
    await api.search(['arroz']);
    expect(captured.last.headers.containsKey(ApiClient.analyticsIdHeader),
        isFalse);
    expect(captured.last.body, isNot(contains('excluded_cnpjs')));
  });

  test('disabling usage stats clears the local analytics id', () async {
    SharedPreferences.setMockInitialValues({'analytics_id_v1': 'abc123'});
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await container.read(usageStatsProvider.future);
    await container.read(usageStatsProvider.notifier).set(false);

    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('analytics_id_v1'), isNull);
    expect(container.read(usageStatsProvider).value, isFalse);
  });
}
