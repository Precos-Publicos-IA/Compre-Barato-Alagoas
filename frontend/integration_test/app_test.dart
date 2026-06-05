// End-to-end test driving the real app against a live backend.
// Run on a connected device, pointing at your backend, e.g.:
//   flutter test integration_test/app_test.dart \
//     --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br -d <device-id>
import 'package:compre_barato_alagoas/main.dart' as app;
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

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

    // Search and wait for the backend round-trip.
    await tester.tap(find.text('VER PREÇOS'));
    await tester.pumpAndSettle(const Duration(seconds: 6));

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

    // Back to the search screen — the basket we just searched is now saved.
    await tester.tap(find.text('EDITAR LISTA'));
    await tester.pumpAndSettle();
    // Clear the current basket so the "Listas recentes" section shows.
    await tester.tap(find.byTooltip('Remover').first);
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Remover').first);
    await tester.pumpAndSettle();
    expect(find.text('Listas recentes'), findsOneWidget);
  });
}
