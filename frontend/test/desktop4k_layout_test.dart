import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:compre_barato_alagoas/features/search/search_screen.dart';
import 'package:compre_barato_alagoas/core/theme.dart';
import 'package:compre_barato_alagoas/core/layout.dart';
import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:compre_barato_alagoas/data/models.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<void> _pumpSearchAt(WidgetTester tester, Size physical) async {
  final view = tester.view;
  view.physicalSize = physical;
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
  // Avoid pumpAndSettle — home can keep animating.
  await tester.pump();
  for (var i = 0; i < 20; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('contentMaxWidth is generous on QHD and 4K', () {
    double maxW(double w) {
      if (w >= 3200) return (w * 0.48).clamp(1400.0, 1920.0);
      if (w >= 2400) return (w * 0.52).clamp(1180.0, 1560.0);
      if (w >= 1600) return 920;
      if (w >= 1100) return 760;
      return double.infinity;
    }

    expect(maxW(2560), closeTo(1331.2, 0.1));
    expect(maxW(3840), closeTo(1843.2, 0.1));
    expect(maxW(2560), greaterThan(1100));
    expect(maxW(3840), greaterThan(1200));
  });

  testWidgets('SearchScreen paints tips + headline at QHD', (tester) async {
    await _pumpSearchAt(tester, const Size(2560, 1440));

    expect(AppLayout.isDesktop4k(tester.element(find.byType(SearchScreen))), isTrue);
    expect(
      AppLayout.contentMaxWidth(tester.element(find.byType(SearchScreen))),
      closeTo(1331.2, 0.5),
    );
    expect(find.textContaining('precisa comprar'), findsOneWidget);
    expect(find.text('VER PREÇOS'), findsOneWidget);
    expect(find.textContaining('Como economizar'), findsOneWidget);
  });

  testWidgets('SearchScreen paints tips + headline at 4K', (tester) async {
    await _pumpSearchAt(tester, const Size(3840, 2160));

    expect(AppLayout.isDesktop4k(tester.element(find.byType(SearchScreen))), isTrue);
    expect(
      AppLayout.contentMaxWidth(tester.element(find.byType(SearchScreen))),
      closeTo(1843.2, 0.5),
    );
    expect(find.text('VER PREÇOS'), findsOneWidget);
    expect(find.textContaining('Como economizar'), findsOneWidget);
  });
}
