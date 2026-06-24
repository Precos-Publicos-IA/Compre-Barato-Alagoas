import 'package:compre_barato_alagoas/data/models.dart';
import 'package:compre_barato_alagoas/features/results/savings.dart';
import 'package:compre_barato_alagoas/features/share/share_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

StoreResult _store(String name, double total, int found) => StoreResult(
      cnpj: name,
      name: name,
      itemsFound: found,
      itemsTotal: 3,
      total: total,
      items: const [],
      missing: const [],
    );

void main() {
  group('share link', () {
    test('builds a short /abrir/<uuid> link from the list id', () {
      final link = buildShareLink('abc123');
      expect(link.path, '/abrir/abc123');
      expect(parseSharedListId(link), 'abc123');
    });

    test('parses the list id from an incoming link', () {
      expect(parseSharedListId(Uri.parse('https://x/abrir/xyz')), 'xyz');
      expect(parseSharedListId(Uri.parse('https://x/abrir')), isNull);
      expect(parseSharedListId(Uri.parse('https://x/abrir/')), isNull);
      expect(parseSharedListId(Uri.parse('https://x/outra/xyz')), isNull);
    });

    test('message includes the savings amount when positive', () {
      final msg = buildShareMessage('abc123', 12.5);
      expect(msg, contains('R\$ 12,50'));
      expect(msg, contains('/abrir/abc123'));
    });

    test('message is generic when there is no saving', () {
      final msg = buildShareMessage('abc123', 0);
      expect(msg, isNot(contains('desconto de R\$')));
      expect(msg, contains('/abrir/abc123'));
    });
  });

  group('shareOriginFromContext', () {
    testWidgets('returns a non-zero Rect from a laid-out widget', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 120,
                height: 48,
                child: Placeholder(),
              ),
            ),
          ),
        ),
      );
      final element = tester.element(find.byType(Placeholder));
      final origin = shareOriginFromContext(element);
      expect(origin, isNotNull);
      expect(origin!.width, greaterThan(0));
      expect(origin.height, greaterThan(0));
    });

    test('shareSavings no-ops on empty listId without throwing', () async {
      await shareSavings('', 10.0);
    });
  });

  group('computeSavings', () {
    test('compares only stores that found the most items', () {
      final s = computeSavings([
        _store('A', 10.0, 3),
        _store('B', 14.0, 3),
        _store('C', 5.0, 1), // half-empty basket, must be ignored
      ]);
      expect(s, isNotNull);
      expect(s!.amount, closeTo(4.0, 1e-9)); // 14 - 10, not 14 - 5
      expect(s.cheapest.name, 'A');
      expect(s.comparedStores, 2);
    });

    test('null when only one comparable store (#410)', () {
      final s = computeSavings([_store('A', 10.0, 3), _store('B', 9.0, 2)]);
      expect(s, isNull);
    });

    test('null when two stores have equal totals', () {
      final s = computeSavings([
        _store('A', 10.0, 3),
        _store('B', 10.0, 3),
      ]);
      expect(s, isNull);
    });
  });
}
