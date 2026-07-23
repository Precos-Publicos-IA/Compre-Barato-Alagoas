import 'package:compre_barato_alagoas/features/results/search_wait_copy.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('ETA is 5 min for small baskets and 10 min for larger ones', () {
    expect(estimateSearchEtaMinutes(0), 5);
    expect(estimateSearchEtaMinutes(1), 5);
    expect(estimateSearchEtaMinutes(5), 5);
    expect(estimateSearchEtaMinutes(6), 10);
    expect(estimateSearchEtaMinutes(20), 10);
  });

  test('rotating phrases wrap and stay non-empty', () {
    expect(kSearchWaitPhrases, isNotEmpty);
    expect(searchWaitPhraseAt(0), kSearchWaitPhrases.first);
    expect(
      searchWaitPhraseAt(kSearchWaitPhrases.length),
      kSearchWaitPhrases.first,
    );
    expect(searchWaitPhraseAt(1), contains('preços'));
  });

  test('explainer and notify lines mention ETA minutes', () {
    final explainer = searchWaitExplainer(etaMinutes: 5);
    expect(explainer, contains('5 min'));
    expect(explainer.toLowerCase(), contains('nfc-e'));

    final withNotify = searchWaitNotifyLine(etaMinutes: 10, canNotify: true);
    expect(withNotify, contains('notificação'));
    expect(withNotify, contains('10 min'));

    final noNotify = searchWaitNotifyLine(etaMinutes: 5, canNotify: false);
    expect(noNotify, contains('5 min'));
    expect(noNotify.toLowerCase(), contains('notifica'));

    final web = searchWaitNotifyLine(
      etaMinutes: 5,
      canNotify: false,
      isWeb: true,
    );
    expect(web, contains('5 min'));
    expect(web, contains('nesta tela'));
  });
}
