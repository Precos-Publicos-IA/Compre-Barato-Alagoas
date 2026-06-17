import 'package:compre_barato_alagoas/data/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('SearchResponse.fromJson parses a full payload', () {
    final json = {
      'origin': {'latitude': -9.6498, 'longitude': -35.7089},
      'radius_km': 8,
      'days': 7,
      'items_requested': 2,
      'data_source': 'mock',
      'stores': [
        {
          'cnpj': '123',
          'name': 'Mercado X',
          'latitude': -9.65,
          'longitude': -35.70,
          'address': 'Rua A, 1',
          'bairro': 'Centro',
          'distance_km': 1.2,
          'items_found': 1,
          'items_total': 2,
          'total': 9.99,
          'items': [
            {
              'query': 'arroz',
              'found': true,
              'description': 'ARROZ 5KG',
              'price': 24.9,
              'unit_price': 4.98,
              'base_unit': 'kg',
              'quantity': 5.0,
              'unit': 'kg',
              'quantity_parsed': true,
            }
          ],
          'missing': ['leite'],
        }
      ],
      'metrics': {
        'items_requested': 2,
        'stores_found': 1,
        'match_rate': 0.5,
        'quantity_parse_rate': 1.0,
      },
    };

    final resp = SearchResponse.fromJson(json);
    expect(resp.dataSource, 'mock');
    expect(resp.stores, hasLength(1));
    final store = resp.stores.first;
    expect(store.name, 'Mercado X');
    expect(store.items.first.unitPrice, 4.98);
    expect(store.missing, ['leite']);
    expect(resp.metrics.matchRate, 0.5);
    // requested_quantity / line_total default when the backend omits them.
    expect(store.items.first.requestedQuantity, 1);
    expect(store.items.first.lineTotal, isNull);
  });

  test('ItemOffer parses requested_quantity and line_total', () {
    final offer = ItemOffer.fromJson({
      'query': '3 arroz',
      'found': true,
      'price': 22.63,
      'requested_quantity': 3,
      'line_total': 67.89,
    });
    expect(offer.requestedQuantity, 3);
    expect(offer.lineTotal, 67.89);
  });
}
