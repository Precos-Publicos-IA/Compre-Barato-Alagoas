import 'dart:io';
import 'dart:ui' as ui;

import 'package:compre_barato_alagoas/core/layout.dart';
import 'package:compre_barato_alagoas/core/theme.dart';
import 'package:compre_barato_alagoas/data/models.dart';
import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:compre_barato_alagoas/features/search/search_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Honest SearchScreen stills at QHD/4K for e2e matrix cells.
///
/// Headless Chrome CanvasKit currently paints blank on this host (local+live).
/// Widget [RepaintBoundary.toImage] still rasterizes the real product UI for
/// V-FORM-FACTOR critique of the Desktop4k layout.
///
///   cd frontend && flutter test test/home_viewport_golden_test.dart
const _kSuggestions = <Suggestion>[
  Suggestion(label: 'Arroz', emoji: '🍚'),
  Suggestion(label: 'Feijão', emoji: '🫘'),
  Suggestion(label: 'Leite', emoji: '🥛'),
  Suggestion(label: 'Ovo', emoji: '🥚'),
  Suggestion(label: 'Açúcar', emoji: '🧂'),
  Suggestion(label: 'Café', emoji: '☕'),
  Suggestion(label: 'Óleo', emoji: '🫒'),
  Suggestion(label: 'Macarrão', emoji: '🍝'),
  Suggestion(label: 'Banana', emoji: '🍌'),
  Suggestion(label: 'Tomate', emoji: '🍅'),
  Suggestion(label: 'Frango', emoji: '🍗'),
  Suggestion(label: 'Refrigerante', emoji: '🥤'),
];

Future<void> _pumpSearchAt(WidgetTester tester, Size logical) async {
  final view = tester.view;
  view.physicalSize = logical;
  view.devicePixelRatio = 1.0;
  addTearDown(view.resetPhysicalSize);
  addTearDown(view.resetDevicePixelRatio);

  await tester.binding.setSurfaceSize(logical);
  addTearDown(() => tester.binding.setSurfaceSize(null));

  await tester.pumpWidget(
    RepaintBoundary(
      key: const ValueKey('home-capture'),
      child: ProviderScope(
        overrides: [
          suggestionsProvider.overrideWith((ref) async => _kSuggestions),
        ],
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: buildAppTheme(),
          home: const SearchScreen(),
        ),
      ),
    ),
  );
  await tester.pump();
  for (var i = 0; i < 60; i++) {
    await tester.pump(const Duration(milliseconds: 50));
    if (find.text('Arroz').evaluate().isNotEmpty) break;
  }
  // Extra frames for layout settle (avoid pumpAndSettle — banners may animate).
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<File> _writePng(WidgetTester tester, String outPath) async {
  final boundary = tester.renderObject(
    find.byKey(const ValueKey('home-capture')),
  ) as RenderRepaintBoundary;

  final ui.Image image = await tester.runAsync(
        () => boundary.toImage(pixelRatio: 1.0),
      ) as ui.Image;

  final byteData = await tester.runAsync(
    () => image.toByteData(format: ui.ImageByteFormat.png),
  );
  expect(byteData, isNotNull);

  // Integrity: require non-trivial non-white (canvas F2F5F1 counts).
  final raw = await tester.runAsync(
    () => image.toByteData(format: ui.ImageByteFormat.rawRgba),
  );
  final px = raw!.buffer.asUint8List();
  var nonWhite = 0;
  for (var i = 0; i < px.length; i += 4) {
    if (px[i] < 250 || px[i + 1] < 250 || px[i + 2] < 250) nonWhite++;
  }
  final total = image.width * image.height;
  final pct = 100.0 * nonWhite / total;
  // ignore: avoid_print
  print(
    'CAPTURE ${image.width}x${image.height} nonWhite=${pct.toStringAsFixed(1)}% '
    '→ $outPath',
  );
  expect(pct, greaterThan(20), reason: 'still looks blank/white');

  final file = File(outPath);
  file.parent.createSync(recursive: true);
  file.writeAsBytesSync(byteData!.buffer.asUint8List());
  image.dispose();
  return file;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    final binding = TestWidgetsFlutterBinding.instance;
    binding.platformDispatcher.textScaleFactorTestValue = 1.0;
  });

  tearDown(() {
    final binding = TestWidgetsFlutterBinding.instance;
    binding.platformDispatcher.clearAllTestValues();
  });

  testWidgets('export qhd_01_home (2560×1440 Desktop4k)', (tester) async {
    await _pumpSearchAt(tester, const Size(2560, 1440));

    expect(AppLayout.isDesktop4k(tester.element(find.byType(SearchScreen))), isTrue);
    expect(
      AppLayout.contentMaxWidth(tester.element(find.byType(SearchScreen))),
      closeTo(1331.2, 0.5),
    );
    expect(find.text('VER PREÇOS'), findsOneWidget);
    expect(find.textContaining('precisa comprar'), findsOneWidget);
    expect(find.textContaining('Como economizar'), findsOneWidget);

    final f = await _writePng(
      tester,
      '../e2e/screenshots/viewports/qhd_01_home.png',
    );
    expect(f.lengthSync(), greaterThan(20000));
  }, timeout: const Timeout(Duration(minutes: 3)));

  testWidgets('export 4k_01_home (3840×2160 Desktop4k)', (tester) async {
    await _pumpSearchAt(tester, const Size(3840, 2160));

    expect(AppLayout.isDesktop4k(tester.element(find.byType(SearchScreen))), isTrue);
    expect(
      AppLayout.contentMaxWidth(tester.element(find.byType(SearchScreen))),
      closeTo(1843.2, 0.5),
    );
    expect(find.text('VER PREÇOS'), findsOneWidget);
    expect(find.textContaining('Como economizar'), findsOneWidget);

    final f = await _writePng(
      tester,
      '../e2e/screenshots/viewports/4k_01_home.png',
    );
    expect(f.lengthSync(), greaterThan(30000));
  }, timeout: const Timeout(Duration(minutes: 5)));
}
