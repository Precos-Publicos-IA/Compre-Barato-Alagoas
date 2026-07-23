import 'package:compre_barato_alagoas/data/models.dart';
import 'package:compre_barato_alagoas/features/results/feedback_payload.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('itemDescriptionsFromResults', () {
    test('maps query to first non-empty product description', () {
      final stores = [
        StoreResult(
          cnpj: '1',
          name: 'A',
          itemsFound: 1,
          itemsTotal: 1,
          total: 10,
          items: const [
            ItemOffer(
              query: 'Arroz',
              found: true,
              description: 'ARROZ TIPO 1 5KG',
              price: 20,
            ),
          ],
          missing: const [],
        ),
        StoreResult(
          cnpj: '2',
          name: 'B',
          itemsFound: 1,
          itemsTotal: 1,
          total: 12,
          items: const [
            ItemOffer(
              query: 'Arroz',
              found: true,
              description: 'ARROZ OUTRO',
              price: 22,
            ),
          ],
          missing: const [],
        ),
      ];
      final map = itemDescriptionsFromResults(
        stores,
        preferredQueries: const ['Arroz'],
      );
      expect(map['Arroz'], 'ARROZ TIPO 1 5KG');
    });

    test('skips not-found and empty descriptions', () {
      final stores = [
        StoreResult(
          cnpj: '1',
          name: 'A',
          itemsFound: 0,
          itemsTotal: 1,
          total: 0,
          items: const [
            ItemOffer(query: 'Leite', found: false, description: 'X'),
            ItemOffer(query: 'Ovos', found: true, description: '  '),
            ItemOffer(
              query: 'Feijão',
              found: true,
              description: 'FEIJAO PRETO 1KG',
            ),
          ],
          missing: const ['Leite'],
        ),
      ];
      final map = itemDescriptionsFromResults(
        stores,
        preferredQueries: const ['Leite', 'Ovos', 'Feijão'],
      );
      expect(map.containsKey('Leite'), isFalse);
      expect(map.containsKey('Ovos'), isFalse);
      expect(map['Feijão'], 'FEIJAO PRETO 1KG');
    });

    test('matches preferred query case-insensitively', () {
      final stores = [
        StoreResult(
          cnpj: '1',
          name: 'A',
          itemsFound: 1,
          itemsTotal: 1,
          total: 5,
          items: const [
            ItemOffer(
              query: 'pão francês',
              found: true,
              description: 'PAO FRANCES UN',
            ),
          ],
          missing: const [],
        ),
      ];
      final map = itemDescriptionsFromResults(
        stores,
        preferredQueries: const ['Pão Francês'],
      );
      expect(map['Pão Francês'], 'PAO FRANCES UN');
    });
  });

  group('wrongItemFeedbackBody', () {
    test('includes query, item, and non-empty description (6-S3)', () {
      final body = wrongItemFeedbackBody(
        query: 'arroz',
        description: 'FEIJAO PRETO 1KG',
        note: 'saiu feijão',
        listId: 'abc',
      );
      expect(body['kind'], 'wrong_item');
      expect(body['query'], 'arroz');
      expect(body['item'], 'arroz');
      expect(body['description'], 'FEIJAO PRETO 1KG');
      expect(body['note'], 'saiu feijão');
      expect(body['list_id'], 'abc');
    });

    test('omits empty description and note', () {
      final body = wrongItemFeedbackBody(query: 'leite', description: '  ');
      expect(body['query'], 'leite');
      expect(body.containsKey('description'), isFalse);
      expect(body.containsKey('note'), isFalse);
    });
  });
}
