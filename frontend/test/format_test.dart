import 'package:compre_barato_alagoas/core/format.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('formatBRL', () {
    test('formats whole and fractional reais', () {
      expect(formatBRL(5), 'R\$ 5,00');
      expect(formatBRL(4.99), 'R\$ 4,99');
      expect(formatBRL(1234.5), 'R\$ 1.234,50');
    });

    test('rounds to cents', () {
      expect(formatBRL(4.282), 'R\$ 4,28');
    });
  });

  test('formatUnitPrice', () {
    expect(formatUnitPrice(4.98, 'kg'), 'R\$ 4,98 / kg');
  });

  group('formatDistance', () {
    test('metres under 1km', () => expect(formatDistance(0.45), '450 m'));
    test('km otherwise', () => expect(formatDistance(8.68), '8.7 km'));
    test('null', () => expect(formatDistance(null), ''));
  });

  group('formatDate', () {
    test('ISO timestamp to dd/mm/yyyy', () {
      expect(formatDate('2026-06-05T05:55:53Z'), '05/06/2026');
      expect(formatDate('2026-01-09T23:00:00Z'), '09/01/2026');
    });
    test('null/empty/invalid', () {
      expect(formatDate(null), '');
      expect(formatDate(''), '');
      expect(formatDate('not-a-date'), '');
    });
  });
}
