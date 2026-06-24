import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

/// Derives a non-zero [Rect] for iOS/iPadOS share popover anchoring.
/// UIActivityViewController requires [sharePositionOrigin]; without it
/// `share_plus` can throw or silently fail on iPad / some iOS versions.
Rect? shareOriginFromContext(BuildContext context) {
  final box = context.findRenderObject() as RenderBox?;
  if (box == null || !box.hasSize) return null;
  final offset = box.localToGlobal(Offset.zero);
  final size = box.size;
  if (size.isEmpty) return null;
  return offset & size;
}

/// Opens the native share sheet (WhatsApp, etc.).
///
/// Pass [sharePositionOrigin] (or let [context] derive it) so iOS/iPadOS can
/// present the popover. On failure, falls back to copying the message to the
/// clipboard and shows a [SnackBar] when [context] is provided.
Future<void> shareSavings(
  String listId,
  double savings, {
  BuildContext? context,
  Rect? sharePositionOrigin,
}) async {
  if (listId.isEmpty) return;
  final message = buildShareMessage(listId, savings);
  final origin = sharePositionOrigin ??
      (context != null ? shareOriginFromContext(context) : null);

  try {
    await Share.share(
      message,
      subject: 'Compre Barato Alagoas',
      sharePositionOrigin: origin,
    );
  } catch (_) {
    // iOS Safari / iPad may reject share without a valid origin or user gesture.
    // Clipboard is a pragmatic fallback so the share link is not lost.
    try {
      await Clipboard.setData(ClipboardData(text: message));
      if (context != null && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Não foi possível abrir o compartilhamento. '
              'Link copiado para a área de transferência.',
            ),
          ),
        );
      }
    } catch (_) {
      if (context != null && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Não foi possível compartilhar. Tente novamente.'),
          ),
        );
      }
    }
  }
}
