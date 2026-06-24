import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  ProviderContainer container() => ProviderContainer();

  test('add de-duplicates case-insensitively (#409)', () {
    final c = container();
    addTearDown(c.dispose);
    final basket = c.read(basketProvider.notifier);
    basket.add('Arroz');
    basket.add('arroz');
    basket.add('  ARROZ ');
    expect(c.read(basketProvider), ['Arroz']);
  });

  test('add caps the basket at kMaxBasketItems (#340)', () {
    final c = container();
    addTearDown(c.dispose);
    final basket = c.read(basketProvider.notifier);
    for (var i = 0; i < kMaxBasketItems + 10; i++) {
      basket.add('item $i');
    }
    expect(c.read(basketProvider).length, kMaxBasketItems);
  });

  test('addMany stops at the cap (#340)', () {
    final c = container();
    addTearDown(c.dispose);
    final basket = c.read(basketProvider.notifier);
    basket.addMany([for (var i = 0; i < 50; i++) 'item $i']);
    expect(c.read(basketProvider).length, kMaxBasketItems);
  });
}
