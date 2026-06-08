import 'package:compre_barato_alagoas/data/analytics_id.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // Regression: on a web build where `shared_preferences` isn't registered,
  // `SharedPreferences.getInstance()` throws MissingPluginException. The analytics
  // id is a non-essential convenience and MUST NOT let that abort the core search
  // (the bug behind "web search not working"). With no mock prefs set here, the
  // platform channel is unregistered, reproducing exactly that condition.
  TestWidgetsFlutterBinding.ensureInitialized();

  test('getOrCreate falls back to an in-memory id when storage is unavailable',
      () async {
    final id = await AnalyticsId().getOrCreate();
    expect(id, matches(RegExp(r'^[0-9a-f]{40}$')));
  });

  test('getOrCreate is stable within a session even without storage', () async {
    final a = AnalyticsId();
    final first = await a.getOrCreate();
    expect(await a.getOrCreate(), equals(first));
  });
}
