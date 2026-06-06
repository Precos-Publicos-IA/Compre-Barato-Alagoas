// End-to-end test driving the real app against a live backend.
// Run on a connected device, pointing at your backend, e.g.:
//   flutter test integration_test/app_test.dart \
//     --dart-define=API_BASE_URL=https://alagoas.precospublicos.ia.br -d <device-id>
import 'package:compre_barato_alagoas/main.dart' as app;
import 'package:flutter/material.dart';
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

    // Feedback card at the bottom: send a 👍 to the live backend.
    await tester.scrollUntilVisible(
      find.text('Este resultado foi útil?'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Sim'));
    await tester.pumpAndSettle(const Duration(seconds: 2));
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
}
