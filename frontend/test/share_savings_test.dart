import 'package:compre_barato_alagoas/data/models.dart';
import 'package:compre_barato_alagoas/features/results/savings.dart';
import 'package:compre_barato_alagoas/features/share/share_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

StoreResult _store(
  String name,
  double total,
  int found, {
  int itemsTotal = 3,
}) =>
    StoreResult(
      cnpj: name,
      name: name,
      itemsFound: found,
      itemsTotal: itemsTotal,
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

    test('zero savings when only one comparable store', () {
      final s = computeSavings([_store('A', 10.0, 3), _store('B', 9.0, 2)]);
      expect(s!.amount, 0);
      expect(s.cheapest.name, 'A');
    });
  });

  group('BasketCoverage / primary savings gate (PR3 honesty)', () {
    test('computeCoverage uses max found and basket total', () {
      final c = computeCoverage([
        _store('A', 10.0, 4, itemsTotal: 10),
        _store('B', 12.0, 3, itemsTotal: 10),
      ]);
      expect(c.found, 4);
      expect(c.total, 10);
      expect(c.fraction, closeTo(0.4, 1e-9));
      expect(c.isComplete, isFalse);
      expect(c.allowsPrimarySavings, isFalse);
    });

    test('full basket allows primary savings', () {
      final c = computeCoverage([
        _store('A', 10.0, 10, itemsTotal: 10),
        _store('B', 15.0, 10, itemsTotal: 10),
      ]);
      expect(c.isComplete, isTrue);
      expect(c.allowsPrimarySavings, isTrue);
    });

    test('threshold 0.7: 7/10 allows, 6/10 does not', () {
      final ok = BasketCoverage(found: 7, total: 10);
      final no = BasketCoverage(found: 6, total: 10);
      expect(ok.fraction, closeTo(0.7, 1e-9));
      expect(ok.allowsPrimarySavings, isTrue);
      expect(no.allowsPrimarySavings, isFalse);
    });

    test('phone case 4/10 never allows primary economize claim', () {
      final c = BasketCoverage(found: 4, total: 10);
      expect(c.allowsPrimarySavings, isFalse);
      expect(c.partialHeroTitle, 'Encontramos 4 de 10 itens');
      expect(c.partialHeroSubtitle, contains('Compare só o que tem preço'));
    });

    test('shouldShowPrimarySavings requires amount > 0 and coverage', () {
      final storesFull = [
        _store('A', 10.0, 10, itemsTotal: 10),
        _store('B', 15.0, 10, itemsTotal: 10),
      ];
      final storesPartial = [
        _store('A', 10.0, 4, itemsTotal: 10),
        _store('B', 15.64, 4, itemsTotal: 10), // fake R$ 5,64 gap
      ];

      final fullSav = computeSavings(storesFull)!;
      final partSav = computeSavings(storesPartial)!;
      final fullCov = computeCoverage(storesFull);
      final partCov = computeCoverage(storesPartial);

      expect(fullSav.amount, closeTo(5.0, 1e-9));
      expect(partSav.amount, closeTo(5.64, 1e-9));

      expect(shouldShowPrimarySavings(fullSav, fullCov), isTrue);
      // The bug: partial 4/10 with positive delta must NOT show primary hero.
      expect(shouldShowPrimarySavings(partSav, partCov), isFalse);
      expect(shouldShowPrimarySavings(null, fullCov), isFalse);
      expect(
        shouldShowPrimarySavings(
          const SavingsInfo(
            amount: 0,
            cheapest: StoreResult(
              cnpj: 'x',
              name: 'x',
              itemsFound: 10,
              itemsTotal: 10,
              total: 1,
              items: [],
              missing: [],
            ),
            comparedStores: 1,
          ),
          fullCov,
        ),
        isFalse,
      );
    });

    test('empty store list coverage is zero', () {
      final c = computeCoverage(const []);
      expect(c.found, 0);
      expect(c.total, 0);
      expect(c.allowsPrimarySavings, isFalse);
    });
  });
}
