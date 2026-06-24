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

  group('brazilCivilDateTime', () {
    test('applies fixed UTC-3 offset (America/Maceio)', () {
      final utc = DateTime.utc(2026, 1, 10, 2, 0); // 02:00 UTC
      final br = brazilCivilDateTime(utc);
      // 02:00 UTC → 23:00 previous evening in Maceió
      expect(br.year, 2026);
      expect(br.month, 1);
      expect(br.day, 9);
      expect(br.hour, 23);
    });

    test('offset constant is -3 hours', () {
      expect(kBrazilUtcOffset, const Duration(hours: -3));
    });
  });

  group('formatDate', () {
    test('ISO UTC timestamp uses Brazil civil day', () {
      expect(formatDate('2026-06-05T05:55:53Z'), '05/06/2026');
      // 23:00 UTC is still 20:00 same calendar day in Maceió
      expect(formatDate('2026-01-09T23:00:00Z'), '09/01/2026');
    });

    test('late UTC evening rolls to previous day in Brazil (issue #59)', () {
      // 02:00 UTC on 10 Jan = 23:00 on 9 Jan in America/Maceio
      expect(formatDate('2026-01-10T02:00:00Z'), '09/01/2026');
      // 03:00 UTC on 10 Jan = midnight 10 Jan in Maceió
      expect(formatDate('2026-01-10T03:00:00Z'), '10/01/2026');
    });

    test('offset timestamps convert via UTC then Brazil offset', () {
      expect(formatDate('2026-01-10T00:00:00+00:00'), '09/01/2026'); // 21:00 prev day BR
    });

    test('date-only strings keep the written calendar day', () {
      expect(formatDate('2026-06-05'), '05/06/2026');
    });

    test('null/empty/invalid', () {
      expect(formatDate(null), '');
      expect(formatDate(''), '');
      expect(formatDate('not-a-date'), '');
    });
  });
}
