import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('add accepts up to kMaxBasketItems then rejects', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final basket = container.read(basketProvider.notifier);

    for (var i = 0; i < kMaxBasketItems; i++) {
      expect(basket.add('item $i'), isTrue);
    }
    expect(container.read(basketProvider).length, kMaxBasketItems);
    expect(basket.isFull, isTrue);
    expect(basket.add('overflow'), isFalse);
    expect(container.read(basketProvider).length, kMaxBasketItems);
  });

  test('addMany stops at max and returns count added', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final basket = container.read(basketProvider.notifier);

    final many = List.generate(40, (i) => 'x$i');
    final added = basket.addMany(many);
    expect(added, kMaxBasketItems);
    expect(container.read(basketProvider).length, kMaxBasketItems);
  });

  test('add dedupes case-insensitively without counting toward waste', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final basket = container.read(basketProvider.notifier);
    expect(basket.add('Arroz'), isTrue);
    expect(basket.add('arroz'), isFalse);
    expect(container.read(basketProvider), ['Arroz']);
  });
}
