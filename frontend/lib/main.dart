import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme.dart';
import 'data/api_client.dart';
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
    _linkSub = _appLinks.uriLinkStream.listen(
      _handleUri,
      onError: (_) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          final ctx = _navKey.currentContext;
          if (ctx == null) return;
          ScaffoldMessenger.of(ctx).showSnackBar(
            const SnackBar(
              content: Text(
                'Não foi possível abrir o link compartilhado. Tente de novo.',
              ),
            ),
          );
        });
      },
    );
  }

  void _snackOnHome(String message) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _navKey.currentState?.popUntil((r) => r.isFirst);
      final ctx = _navKey.currentContext;
      if (ctx != null) {
        ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(message)));
      }
    });
  }

  Future<void> _handleUri(Uri uri) async {
    final listId = parseSharedListId(uri);
    if (listId == null) return;
    _handledInitial = true;
    // null = expired/missing; ApiException/transport = temporary or invalid (#390/#371).
    List<String>? items;
    Object? fetchError;
    try {
      items = await ref.read(apiClientProvider).fetchList(listId);
    } catch (e) {
      fetchError = e;
      items = null;
    }
    if (fetchError != null) {
      if (fetchError is ApiException && fetchError.isInvalidListId) {
        _snackOnHome(
          'Este link não é válido. Confira se copiou o endereço completo.',
        );
      } else if (fetchError is ApiException) {
        _snackOnHome(fetchError.message);
      } else {
        _snackOnHome(
          'Sem conexão para abrir o link. Verifique a rede e tente de novo.',
        );
      }
      return;
    }
    if (items == null || items.isEmpty) {
      _snackOnHome('Esse link expirou ou não está mais disponível.');
      return;
    }
    final resolved = items;
    // Defer until the navigator + providers are ready.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // Reset stack so a second /abrir does not stack ResultsScreens (#373).
      _navKey.currentState?.popUntil((r) => r.isFirst);
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
