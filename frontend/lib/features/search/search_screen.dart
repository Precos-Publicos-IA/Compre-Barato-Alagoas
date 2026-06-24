import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../data/providers.dart';
import '../../data/recent_lists.dart';
import '../privacy/cloud_sync_sheet.dart';
import '../results/results_screen.dart';
import '../settings/settings_sheet.dart';
import '../stores/store_prefs_sheet.dart';
import 'apk_banner.dart';
import 'voice_input.dart';

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _controller = TextEditingController();
  final _voice = VoiceInput();
  bool _listening = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _dismissKeyboard() {
    FocusManager.instance.primaryFocus?.unfocus();
  }

  void _addCurrent() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    ref.read(basketProvider.notifier).add(text);
    _controller.clear();
    _dismissKeyboard();
  }

  Future<void> _toggleVoice() async {
    if (_listening) {
      await _voice.stop();
      setState(() => _listening = false);
      _addCurrent();
      return;
    }
    final ok = await _voice.start(
      onResult: (text, isFinal) {
        _controller.text = text;
        _controller.selection =
            TextSelection.collapsed(offset: text.length);
        if (isFinal) {
          _addCurrent(); // also dismisses keyboard via _dismissKeyboard
          setState(() => _listening = false);
        }
      },
    );
    if (!ok) {
      if (mounted) await _showVoiceUnavailable();
      return;
    }
    setState(() => _listening = true);
  }

  /// Differentiates permanently-denied mic (Settings path) from other failures (#356).
  Future<void> _showVoiceUnavailable() async {
    final needsSettings = !kIsWeb && _voice.micNeedsSystemSettings;
    if (!needsSettings) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Voz indisponível neste aparelho (microfone ou reconhecimento '
            'de fala). Digite o item ou tente outro idioma nas ajustes do sistema.',
          ),
        ),
      );
      return;
    }
    final open = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Microfone bloqueado'),
        content: const Text(
          'O acesso ao microfone foi negado nas configurações do aparelho. '
          'Abra as configurações do app, permita o microfone e tente de novo. '
          'Enquanto isso, você pode digitar os itens da lista.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Agora não'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Abrir configurações'),
          ),
        ],
      ),
    );
    if (open == true) {
      await openAppSettings();
    }
  }

  void _goToResults() {
    final basket = ref.read(basketProvider);
    if (basket.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Adicione pelo menos um item.')),
      );
      return;
    }
    _dismissKeyboard();
    ref.read(recentListsProvider.notifier).record(basket);
    ref.read(searchControllerProvider.notifier).run(basket);
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const ResultsScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final basket = ref.watch(basketProvider);
    final suggestions = ref.watch(suggestionsProvider);
    final cloudOn = ref.watch(cloudSyncProvider).asData?.value ?? false;

    return Scaffold(
      appBar: AppBar(
        centerTitle: true,
        actions: [
          IconButton(
            tooltip: 'Salvar listas na nuvem',
            icon: Icon(cloudOn ? Icons.cloud_done : Icons.cloud_outlined),
            onPressed: () => CloudSyncSheet.show(context),
          ),
          PopupMenuButton<String>(
            tooltip: 'Mais opções',
            onSelected: (value) {
              switch (value) {
                case 'stores':
                  StorePrefsSheet.show(context);
                case 'settings':
                  SettingsSheet.show(context);
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(
                value: 'stores',
                child: ListTile(
                  leading: Icon(Icons.storefront),
                  title: Text('Minhas lojas'),
                ),
              ),
              PopupMenuItem(
                value: 'settings',
                child: ListTile(
                  leading: Icon(Icons.settings),
                  title: Text('Configurações'),
                ),
              ),
            ],
          ),
        ],
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset('assets/icon/logo.png', height: 32, width: 32),
            const SizedBox(width: 8),
            const Flexible(
              child: Text(
                'Compre Barato Alagoas',
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const ApkBanner(),
              Text(
                'O que você precisa comprar?',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _addCurrent(),
                      decoration: const InputDecoration(
                        hintText: 'Ex.: arroz, feijão, leite',
                      ),
                      style: const TextStyle(fontSize: 20),
                    ),
                  ),
                  const SizedBox(width: 8),
                  _MicButton(listening: _listening, onTap: _toggleVoice),
                ],
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: _addCurrent,
                  icon: const Icon(Icons.add),
                  label: const Text('Adicionar'),
                ),
              ),
              const SizedBox(height: 8),
              suggestions.when(
                data: (items) => Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final s in items)
                      ActionChip(
                        label: Text('${s.emoji} ${s.label}',
                            style: const TextStyle(fontSize: 16)),
                        onPressed: () {
                          ref.read(basketProvider.notifier).add(s.label);
                          _dismissKeyboard();
                        },
                      ),
                  ],
                ),
                loading: () => const SizedBox.shrink(),
                error: (_, _) => const SizedBox.shrink(),
              ),
              if (basket.isEmpty) _RecentLists(),
              const SizedBox(height: 16),
              if (basket.isNotEmpty) ...[
                Text('Sua lista (${basket.length})',
                    style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
              ],
              for (var i = 0; i < basket.length; i++)
                Card(
                  child: ListTile(
                    title: Text(basket[i],
                        style: const TextStyle(fontSize: 18)),
                    trailing: IconButton(
                      icon: const Icon(Icons.close),
                      tooltip: 'Remover',
                      onPressed: () =>
                          ref.read(basketProvider.notifier).removeAt(i),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: FilledButton.icon(
            onPressed: _goToResults,
            icon: const Icon(Icons.search, size: 28),
            label: const Text('VER PREÇOS'),
          ),
        ),
      ),
    );
  }
}

/// "Listas recentes" — quick re-use of previously searched shopping lists.
/// Only shown when the basket is empty so it doesn't clutter an active list.
class _RecentLists extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recents = ref.watch(recentListsProvider);
    return recents.maybeWhen(
      data: (lists) {
        if (lists.isEmpty) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 16),
            Text('Listas recentes',
                style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            for (final list in lists)
              Card(
                child: ListTile(
                  leading: const Icon(Icons.history),
                  title: Text(list.join(', '),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 16)),
                  trailing: const Icon(Icons.refresh),
                  onTap: () =>
                      ref.read(basketProvider.notifier).addMany(list),
                ),
              ),
          ],
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }
}

class _MicButton extends StatelessWidget {
  const _MicButton({required this.listening, required this.onTap});
  final bool listening;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      label: listening ? 'Parar gravação' : 'Falar item',
      child: Material(
        color: listening ? scheme.error : scheme.primary,
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Icon(
              listening ? Icons.stop : Icons.mic,
              color: Colors.white,
              size: 32,
            ),
          ),
        ),
      ),
    );
  }
}
