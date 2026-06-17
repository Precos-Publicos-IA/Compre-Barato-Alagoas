// End-to-end test driving the real app against a live backend.
// Run on a connected device, pointing at your backend, e.g.:
//   flutter test integration_test/app_test.dart \
//     --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br -d <device-id>
import 'package:compre_barato_alagoas/main.dart' as app;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

/// Pumps until [finder] matches or [timeout] elapses. A live search depends on
/// location resolution + a network round-trip whose latency varies, so we wait for
/// the result to actually render instead of guessing a fixed delay.
Future<void> _pumpUntil(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 25),
}) async {
  final deadline = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(deadline)) {
    await tester.pump(const Duration(milliseconds: 250));
    if (finder.evaluate().isNotEmpty) return;
  }
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('basket search shows ranked stores, savings, and best store',
      (tester) async {
    app.main();
    await tester.pumpAndSettle(const Duration(seconds: 3));

    // Add a couple of common items via the suggestion chips.
    expect(find.text('VER PREÇOS'), findsOneWidget);
    await tester.tap(find.textContaining('Arroz').first);
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('Leite').first);
    await tester.pumpAndSettle();
    expect(find.text('Sua lista (2)'), findsOneWidget);

    // Search and wait for results to actually render. "EDITAR LISTA" appears on the
    // results screen before the async results populate, so wait for the best-store
    // badge, which only exists once ranked stores are in.
    await tester.tap(find.text('VER PREÇOS'));
    await _pumpUntil(tester, find.text('MAIS BARATO'));
    await tester.pumpAndSettle();

    // Results essentials.
    expect(find.text('EDITAR LISTA'), findsOneWidget);
    expect(find.textContaining(RegExp(r'R\$')), findsWidgets);
    // Each item shows the date its price was recorded.
    expect(find.textContaining('preço de'), findsWidgets);
    // The cheapest store is badged.
    expect(find.text('MAIS BARATO'), findsOneWidget);
    // The share affordance is present.
    expect(find.text('COMPARTILHAR ECONOMIA'), findsOneWidget);

    // Expand/collapse the best store: its action buttons toggle visibility.
    // Only the best store starts expanded, so "Mapa" is unique to it.
    expect(find.text('Mapa'), findsOneWidget);
    await tester.tap(find.text('MAIS BARATO')); // tap header to collapse
    await tester.pumpAndSettle();
    expect(find.text('Mapa'), findsNothing);
    await tester.tap(find.text('MAIS BARATO')); // expand again
    await tester.pumpAndSettle();
    expect(find.text('Mapa'), findsOneWidget);

    // Tap the map icon in results app bar (if visible) to simulate opening map view.
    if (find.byIcon(Icons.map).evaluate().isNotEmpty) {
      await tester.tap(find.byIcon(Icons.map));
      await tester.pumpAndSettle(const Duration(seconds: 2));
      // Map screen would be open; go back by pageBack (simulates back navigation).
      await tester.pageBack();
      await tester.pumpAndSettle();
    }

    // Feedback card at the bottom: send a 👍 to the live backend.
    await tester.scrollUntilVisible(
      find.text('Este resultado foi útil?'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Sim'));
    await _pumpUntil(tester, find.text('Obrigado pelo feedback!'));
    await tester.pumpAndSettle();
    expect(find.text('Obrigado pelo feedback!'), findsOneWidget);

    // Back to the search screen — the basket we just searched is now saved.
    await tester.tap(find.text('EDITAR LISTA'));
    await tester.pumpAndSettle();
    // Clear the current basket so the "Listas recentes" section shows.
    await tester.tap(find.byTooltip('Remover').first);
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Remover').first);
    await tester.pumpAndSettle();
    expect(find.text('Listas recentes'), findsOneWidget);

    // "Minhas lojas" (StorePrefs multi-store sheet) is reachable from the search
    // screen's "Mais opções" menu and lists ocultas/favoritas.
    await tester.tap(find.byTooltip('Mais opções'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Minhas lojas'));
    await tester.pumpAndSettle(const Duration(seconds: 2));
    expect(find.textContaining('Ocultas'), findsOneWidget);
    expect(find.textContaining('Favoritas'), findsOneWidget);
    await tester.tapAt(const Offset(20, 20));
    await tester.pumpAndSettle();
  });

  testWidgets('cloud sync: consent opt-in then LGPD erasure (live backend)',
      (tester) async {
    app.main();
    await tester.pumpAndSettle(const Duration(seconds: 3));

    // Open the cloud-sync sheet from the app-bar action.
    await tester.tap(find.byTooltip('Salvar listas na nuvem'));
    await tester.pumpAndSettle();
    expect(find.text('Salvar minhas listas na nuvem'), findsOneWidget);

    // Opt in → registers consent + a device record on the live server.
    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle(const Duration(seconds: 4));

    // The privacy policy is reachable from here.
    expect(find.text('Política de Privacidade e Termos'), findsOneWidget);

    // Opt out → LGPD erasure of everything stored for this device.
    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle(const Duration(seconds: 4));

    // Close the sheet; the app stays usable.
    await tester.tapAt(const Offset(20, 20));
    await tester.pumpAndSettle();
    expect(find.text('VER PREÇOS'), findsOneWidget);
  });

  testWidgets('quantities scale the basket and show "N × price" (live backend)',
      (tester) async {
    app.main();
    await tester.pumpAndSettle(const Duration(seconds: 3));

    // Type a quantity item ("3 arroz") and add it to the basket.
    await tester.enterText(find.byType(TextField).first, '3 arroz');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Adicionar'));
    await tester.pumpAndSettle();
    expect(find.text('Sua lista (1)'), findsOneWidget);

    // Search and wait for results to render. The cheapest store starts expanded; its
    // arroz line shows the "3 × R$ …" breakdown produced by the requested-quantity
    // feature, so wait for that text directly.
    await tester.tap(find.text('VER PREÇOS'));
    await _pumpUntil(tester, find.textContaining('3 ×'));
    await tester.pumpAndSettle();

    expect(find.text('EDITAR LISTA'), findsOneWidget);
    expect(find.textContaining('3 ×'), findsWidgets);
  });

  testWidgets('settings: search-param steppers adjust + reset (Configurações)',
      (tester) async {
    app.main();
    await tester.pumpAndSettle(const Duration(seconds: 3));

    // Open Configurações from the "Mais opções" menu.
    await tester.tap(find.byTooltip('Mais opções'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Configurações'));
    await tester.pumpAndSettle();

    expect(find.text('Parâmetros de busca'), findsOneWidget);
    expect(find.text('Distância máxima'), findsOneWidget);

    // Normalize to defaults first (state persists on-device between runs).
    await tester.tap(find.textContaining('Restaurar padrões'));
    await tester.pumpAndSettle();
    expect(find.text('8 km'), findsOneWidget);
    expect(find.text('7 dias'), findsOneWidget);

    // Increase the radius by one step.
    await tester.tap(find.byIcon(Icons.add_circle_outline).first);
    await tester.pumpAndSettle();
    expect(find.text('9 km'), findsOneWidget);

    // Reset back to defaults (also leaves the device in a clean state).
    await tester.tap(find.textContaining('Restaurar padrões'));
    await tester.pumpAndSettle();
    expect(find.text('8 km'), findsOneWidget);
  });
}
