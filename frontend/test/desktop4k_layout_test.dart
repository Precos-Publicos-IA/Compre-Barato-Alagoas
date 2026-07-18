import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:compre_barato_alagoas/features/search/search_screen.dart';
import 'package:compre_barato_alagoas/core/theme.dart';
import 'package:compre_barato_alagoas/core/layout.dart';
import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:compre_barato_alagoas/data/models.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('contentMaxWidth is generous on QHD and 4K', () {
    // pure function via MediaQuery-less clamp logic mirror
    double maxW(double w) {
      if (w >= 3200) return (w * 0.48).clamp(1400.0, 1920.0);
      if (w >= 2400) return (w * 0.52).clamp(1180.0, 1560.0);
      if (w >= 1600) return 920;
      if (w >= 1100) return 760;
      return double.infinity;
    }
    expect(maxW(2560), closeTo(1331.2, 0.1)); // 0.52*2560
    expect(maxW(3840), closeTo(1843.2, 0.1)); // 0.48*3840
    expect(maxW(2560), greaterThan(1100)); // old was 960
    expect(maxW(3840), greaterThan(1200)); // old was 1100
  });

  testWidgets('SearchScreen paints tips + headline at QHD', (tester) async {
    final view = tester.view;
    view.physicalSize = const Size(2560, 1440);
    view.devicePixelRatio = 1.0;
    addTearDown(view.resetPhysicalSize);
    addTearDown(view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          suggestionsProvider.overrideWith((ref) async => const [
                Suggestion(label: 'Arroz', emoji: '🍚'),
                Suggestion(label: 'Feijão', emoji: '🫘'),
              ]),
        ],
        child: MaterialApp(
          theme: buildAppTheme(),
          home: const SearchScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pumpAndSettle(const Duration(seconds: 2));

    expect(AppLayout.isDesktop4k(tester.element(find.byType(SearchScreen))), isTrue);
    expect(AppLayout.contentMaxWidth(tester.element(find.byType(SearchScreen))),
        closeTo(1331.2, 0.5));
    expect(find.textContaining('precisa comprar'), findsOneWidget);
    expect(find.text('VER PREÇOS'), findsOneWidget);
    expect(find.textContaining('Como economizar'), findsOneWidget);
  });
}
