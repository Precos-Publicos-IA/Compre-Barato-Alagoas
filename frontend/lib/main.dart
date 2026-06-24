import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme.dart';
import 'data/providers.dart';
import 'data/recent_lists.dart';
import 'features/results/results_screen.dart';
import 'features/search/search_screen.dart';
import 'features/share/share_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Portrait-only: this app never rotates. Locks the app itself (does NOT touch
  // the phone's system auto-rotate setting).
  SystemChrome.setPreferredOrientations(const [
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  runApp(const ProviderScope(child: CompreBaratoApp()));
}

class CompreBaratoApp extends ConsumerStatefulWidget {
  const CompreBaratoApp({super.key});

  @override
  ConsumerState<CompreBaratoApp> createState() => _CompreBaratoAppState();
}

class _CompreBaratoAppState extends ConsumerState<CompreBaratoApp> {
  final _navKey = GlobalKey<NavigatorState>();
  final _appLinks = AppLinks();
  StreamSubscription<Uri>? _linkSub;
  bool _handledInitial = false;

  @override
  void initState() {
    super.initState();
    _initDeepLinks();
  }

  Future<void> _initDeepLinks() async {
    // Cold start from a shared link.
    try {
      final initial = await _appLinks.getInitialLink();
      if (initial != null) _handleUri(initial);
    } catch (_) {
      // Plugin unavailable (e.g. some web setups) — fall back to the URL below.
    }
    // On web the deep link is just the page URL.
    if (kIsWeb && !_handledInitial) _handleUri(Uri.base);

    // Links that arrive while the app is already running.
    _linkSub = _appLinks.uriLinkStream.listen(_handleUri, onError: (_) {});
  }

  Future<void> _handleUri(Uri uri) async {
    final listId = parseSharedListId(uri);
    if (listId == null) return;
    _handledInitial = true;
    // Resolve the UUID into its shopping list on the backend. A null result
    // means the link expired (30 idle days) or never existed.
    List<String>? items;
    try {
      items = await ref.read(apiClientProvider).fetchList(listId);
    } catch (_) {
      items = null;
    }
    if (items == null || items.isEmpty) {
      // Invalid/expired link → home + recovery options (issue #301), not only a snackbar.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _navKey.currentState?.popUntil((r) => r.isFirst);
        final ctx = _navKey.currentContext;
        if (ctx != null) {
          _showShareLinkRecovery(ctx, listId);
        }
      });
      return;
    }
    final resolved = items;
    // Defer until the navigator + providers are ready.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(basketProvider.notifier)
        ..clear()
        ..addMany(resolved);
      ref.read(recentListsProvider.notifier).record(resolved);
      // Search from the opener's own location.
      ref.read(searchControllerProvider.notifier).run(resolved);
      _navKey.currentState?.push(
        MaterialPageRoute(builder: (_) => const ResultsScreen()),
      );
    });
  }

  /// Expired/invalid /abrir/<uuid>: explain + offer recent lists / retry paste (#301).
  void _showShareLinkRecovery(BuildContext context, String listId) {
    final recents = ref.read(recentListsProvider).asData?.value ?? const [];
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetCtx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Link indisponível',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                Text(
                  'Esse link expirou (listas compartilhadas ficam ~30 dias sem uso) '
                  'ou não existe mais. Código: ${listId.length > 8 ? '${listId.substring(0, 8)}…' : listId}',
                  style: const TextStyle(fontSize: 14, color: Colors.black87),
                ),
                const SizedBox(height: 12),
                const Text(
                  'O que você pode fazer:',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.edit_note),
                  title: const Text('Montar uma lista nova na tela inicial'),
                  subtitle: const Text(
                      'Digite ou fale os itens e busque de novo na sua região'),
                  onTap: () => Navigator.of(sheetCtx).pop(),
                ),
                if (recents.isNotEmpty) ...[
                  const Divider(),
                  const Text('Listas recentes neste aparelho',
                      style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  for (final entry in recents.take(5))
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.history),
                      title: Text(
                        entry.take(3).join(', ') +
                            (entry.length > 3 ? '…' : ''),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      subtitle: Text('${entry.length} item(ns)'),
                      onTap: () {
                        Navigator.of(sheetCtx).pop();
                        ref.read(basketProvider.notifier)
                          ..clear()
                          ..addMany(entry);
                        ref
                            .read(searchControllerProvider.notifier)
                            .run(entry);
                        _navKey.currentState?.push(
                          MaterialPageRoute(
                              builder: (_) => const ResultsScreen()),
                        );
                      },
                    ),
                ],
                const SizedBox(height: 8),
                const Text(
                  'Se quem enviou o link ainda tiver a lista, peça para compartilhar de novo pelo app (botão Compartilhar economia).',
                  style: TextStyle(fontSize: 12, color: Colors.black54),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: () => Navigator.of(sheetCtx).pop(),
                    child: const Text('Entendi'),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
    // Brief snackbar in addition so users who dismiss the sheet still see a cue.
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Esse link expirou ou não está mais disponível.'),
        duration: Duration(seconds: 3),
      ),
    );
  }

  @override
  void dispose() {
    _linkSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Compre Barato Alagoas',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      navigatorKey: _navKey,
      home: const SearchScreen(),
    );
  }
}
