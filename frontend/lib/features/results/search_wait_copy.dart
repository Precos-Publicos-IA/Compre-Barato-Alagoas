/// User-facing copy while a search gathers public NFC-e prices (can be slow).
///
/// Phrases rotate so the wait feels active; ETA is honest (minutes, not seconds).
library;

/// Rotating status lines shown while SEFAZ/web data is being collected.
const kSearchWaitPhrases = <String>[
  'Procurando últimas compras…',
  'Encontrando preços atualizados…',
  'Consultando notas fiscais perto de você…',
  'Comparando ofertas nos mercados…',
  'Coletando dados públicos da SEFAZ-AL…',
  'Montando a cesta mais barata…',
  'Conferindo preços por kg, litro e unidade…',
];

/// How often the loading screen advances to the next phrase.
const kSearchWaitPhrasePeriod = Duration(milliseconds: 3200);

/// Expected wait bucket shown to the user (5 or 10 minutes).
///
/// Cold SEFAZ/web lookups often take tens of seconds per item; multi-item lists
/// stack. We never promise seconds — only coarse minutes.
int estimateSearchEtaMinutes(int itemCount) {
  if (itemCount <= 0) return 5;
  if (itemCount >= 6) return 10;
  return 5;
}

/// Primary explainer under the spinner.
String searchWaitExplainer({required int etaMinutes}) {
  return 'A busca demora um pouco: reunimos compras reais (NFC-e) perto de você. '
      'Tempo estimado: cerca de $etaMinutes min.';
}

/// Promise line about completion notice.
///
/// [canNotify] is true when the OS allows local notifications (or we will try).
/// [isWeb] avoids promising phone notifications in the browser build.
String searchWaitNotifyLine({
  required int etaMinutes,
  required bool canNotify,
  bool isWeb = false,
}) {
  if (isWeb) {
    return 'Quando a busca terminar, o resultado aparece nesta tela. '
        'Tempo estimado: cerca de $etaMinutes min.';
  }
  if (canNotify) {
    return 'Avisamos você com uma notificação quando terminar '
        '(cerca de $etaMinutes min). Pode deixar o app em segundo plano.';
  }
  return 'Quando terminar, o resultado aparece nesta tela. '
      'Tempo estimado: cerca de $etaMinutes min. '
      'Ative notificações nas configurações do aparelho para ser avisado.';
}

/// Phrase at [index], wrapping safely.
String searchWaitPhraseAt(int index) {
  if (kSearchWaitPhrases.isEmpty) return 'Buscando preços…';
  final i = index % kSearchWaitPhrases.length;
  return kSearchWaitPhrases[i < 0 ? 0 : i];
}
