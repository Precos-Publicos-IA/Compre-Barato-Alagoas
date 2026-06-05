import 'package:share_plus/share_plus.dart';

import '../../core/config.dart';
import '../../core/format.dart';

/// Builds the public link for a saved search list. The list is referenced by a
/// short server-side UUID (not the raw items), so links stay short regardless of
/// basket size and identical searches reuse the same id. Whoever opens it
/// searches from *their own* location.
/// On Android the link opens the installed app (App Links); otherwise the web
/// app, which resolves the same UUID.
Uri buildShareLink(String listId) =>
    Uri.parse('${AppConfig.webBaseUrl}${AppConfig.shareLinkPath}/$listId');

/// Extracts the saved-list UUID from an incoming link, i.e. the path segment
/// right after `/abrir`. Returns null if absent.
String? parseSharedListId(Uri uri) {
  final segs = uri.pathSegments;
  final i = segs.indexOf('abrir');
  if (i >= 0 && i + 1 < segs.length && segs[i + 1].trim().isNotEmpty) {
    return segs[i + 1].trim();
  }
  return null;
}

String buildShareMessage(String listId, double savings) {
  final link = buildShareLink(listId).toString();
  if (savings > 0) {
    return 'Encontrei um desconto de ${formatBRL(savings)} usando o app '
        'Compre Barato Alagoas. Veja qual seria o desconto pra você: $link';
  }
  return 'Veja os preços mais baratos perto de você no app '
      'Compre Barato Alagoas: $link';
}

/// Opens the native share sheet (WhatsApp, etc.).
Future<void> shareSavings(String listId, double savings) async {
  if (listId.isEmpty) return;
  await Share.share(
    buildShareMessage(listId, savings),
    subject: 'Compre Barato Alagoas',
  );
}
