import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format.dart';
import '../../data/models.dart';
import '../../data/providers.dart';
import '../map/map_screen.dart';
import '../share/share_service.dart';
import 'savings.dart';
import 'store_card.dart';

class ResultsScreen extends ConsumerWidget {
  const ResultsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final result = ref.watch(searchControllerProvider);
    final basket = ref.watch(basketProvider);

    // SelectionArea lets users copy individual prices/totals on web/desktop and
    // long-press select on mobile (#166); does not block button taps inside.
    return SelectionArea(
      child: Scaffold(
        appBar: AppBar(
          centerTitle: false,
          titleSpacing: 0,
          title: const _AppBarTitle(),
          actions: [
            result.maybeWhen(
              data: (r) => (r != null && r.stores.isNotEmpty)
                  ? IconButton(
                      icon: const Icon(Icons.map),
                      tooltip: 'Ver mapa',
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(
                            builder: (_) => MapScreen(response: r)),
                      ),
                    )
                  : const SizedBox.shrink(),
              orElse: () => const SizedBox.shrink(),
            ),
          ],
        ),
        body: result.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _Message(
            icon: Icons.error_outline,
            text: e.toString(),
            actionLabel: 'Tentar de novo',
            onAction: () =>
                ref.read(searchControllerProvider.notifier).run(basket),
          ),
          data: (r) {
            if (r == null) {
              return const _Message(icon: Icons.search, text: 'Faça uma busca.');
            }
            if (r.stores.isEmpty) {
              return const _Message(
                icon: Icons.sentiment_dissatisfied,
                text: 'Nenhuma loja encontrada por perto.\n'
                    'Experimente termos comuns que as pessoas usam: '
                    '"pão francês", "arroz 5kg", "leite 1L", "feijão", "manteiga". '
                    'Evite marcas muito específicas no começo.',
              );
            }
            return _Results(response: r, items: basket);
          },
        ),
        bottomNavigationBar: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: FilledButton.icon(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.edit),
              label: const Text('EDITAR LISTA'),
            ),
          ),
        ),
      ),
    );
  }
}

class _Results extends ConsumerWidget {
  const _Results({required this.response, required this.items});
  final SearchResponse response;
  final List<String> items;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final avoided = ref.watch(avoidedStoresProvider).asData?.value ?? const {};
    final favorites = ref.watch(favoriteStoresProvider).asData?.value ?? const {};

    // The server already drops hidden stores; this is a belt-and-suspenders guard
    // for results that predate a fresh "ocultar" (e.g. an undo race).
    final visible =
        response.stores.where((s) => !avoided.containsKey(s.cnpj)).toList();
    if (visible.isEmpty) {
      return const _Message(
        icon: Icons.visibility_off,
        text: 'Todas as lojas encontradas estão ocultas.\n'
            'Gerencie em "Minhas lojas".',
      );
    }

    final savings = computeSavings(visible);
    final cheapest = savings?.cheapest ?? visible.first;
    final bestTotal = cheapest.total;

    // Cheapest stays on top (the headline value), then favourites, then the rest —
    // each card still shows its own +R$ delta so the price story is never hidden.
    final ordered = <StoreResult>[
      cheapest,
      ...visible.where(
          (s) => !identical(s, cheapest) && favorites.containsKey(s.cnpj)),
      ...visible.where(
          (s) => !identical(s, cheapest) && !favorites.containsKey(s.cnpj)),
    ];

    return RefreshIndicator(
      onRefresh: () => ref.read(searchControllerProvider.notifier).run(items),
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 16),
        children: [
          if (savings != null && savings.amount > 0)
            _SavingsBanner(savings: savings, listId: response.listId),
          const _FreshnessLine(),
          for (final store in ordered)
            StoreCard(
              store: store,
              isBest: identical(store, cheapest),
              deltaFromBest: store.total - bestTotal,
            ),
          _FeedbackCard(listId: response.listId, items: items),
        ],
      ),
    );
  }
}

/// Lightweight feedback capture under the results. Anonymous and best-effort —
/// it feeds the admin dashboard so we can spot bad AI normalization. Low-text,
/// large touch targets for the low-tech audience.
class _FeedbackCard extends ConsumerStatefulWidget {
  const _FeedbackCard({required this.listId, required this.items});
  final String? listId;
  final List<String> items;

  @override
  ConsumerState<_FeedbackCard> createState() => _FeedbackCardState();
}

class _FeedbackCardState extends ConsumerState<_FeedbackCard> {
  bool _done = false;
  bool _busy = false;

  void _showSendFailed() {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Não foi possível enviar o feedback. Verifique a conexão e tente de novo.',
        ),
      ),
    );
  }

  Future<void> _send({required bool helpful}) async {
    if (_busy) return;
    setState(() => _busy = true);
    final ok = await ref.read(apiClientProvider).submitFeedback(
          kind: 'helpful',
          helpful: helpful,
          listId: widget.listId,
        );
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) {
      setState(() => _done = true);
    } else {
      _showSendFailed();
    }
  }

  Future<void> _report() async {
    final sent = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ReportSheet(items: widget.items, listId: widget.listId),
    );
    if (sent == true && mounted) setState(() => _done = true);
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.fromLTRB(12, 12, 12, 4),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: _done
            ? const Row(
                children: [
                  Icon(Icons.check_circle, color: Colors.green),
                  SizedBox(width: 8),
                  Expanded(child: Text('Obrigado pelo feedback!')),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Este resultado foi útil?',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _send(helpful: true),
                          icon: const Icon(Icons.thumb_up_alt_outlined),
                          label: const Text('Sim'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () => _send(helpful: false),
                          icon: const Icon(Icons.thumb_down_alt_outlined),
                          label: const Text('Não'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: _report,
                    icon: const Icon(Icons.flag_outlined),
                    label: const Text('Reportar item errado'),
                  ),
                ],
              ),
      ),
    );
  }
}

/// Bottom sheet to report a wrong item: pick the item + optional note.
class _ReportSheet extends ConsumerStatefulWidget {
  const _ReportSheet({required this.items, required this.listId});
  final List<String> items;
  final String? listId;

  @override
  ConsumerState<_ReportSheet> createState() => _ReportSheetState();
}

class _ReportSheetState extends ConsumerState<_ReportSheet> {
  String? _item;
  final _note = TextEditingController();
  bool _sending = false;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_sending) return;
    setState(() => _sending = true);
    final ok = await ref.read(apiClientProvider).submitFeedback(
          kind: 'wrong_item',
          item: _item,
          note: _note.text.trim().isEmpty ? null : _note.text.trim(),
          listId: widget.listId,
        );
    if (!mounted) return;
    if (ok) {
      Navigator.of(context).pop(true);
      return;
    }
    setState(() => _sending = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Não foi possível enviar o reporte. Verifique a conexão e tente de novo.',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Reportar item errado',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          if (widget.items.isNotEmpty)
            DropdownButtonFormField<String>(
              initialValue: _item,
              isExpanded: true,
              decoration: const InputDecoration(
                labelText: 'Qual item?',
                border: OutlineInputBorder(),
              ),
              items: [
                for (final it in widget.items)
                  DropdownMenuItem(value: it, child: Text(it)),
              ],
              onChanged: (v) => setState(() => _item = v),
            ),
          const SizedBox(height: 12),
          TextField(
            controller: _note,
            maxLength: 500,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'O que houve? (opcional)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _sending ? null : _submit,
              child: Text(_sending ? 'Enviando…' : 'ENVIAR'),
            ),
          ),
        ],
      ),
    );
  }
}

/// The headline number: how much the user can save. Made deliberately big and
/// loud — most people can't eyeball which basket is cheapest.
class _SavingsBanner extends StatelessWidget {
  const _SavingsBanner({required this.savings, required this.listId});
  final SavingsInfo savings;

  /// Shareable UUID for this search. Null if the server couldn't store it, in
  /// which case the share button is disabled.
  final String? listId;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 12, 12, 4),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: scheme.primary,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.savings, color: scheme.onPrimary, size: 28),
              const SizedBox(width: 8),
              Text('Você pode economizar até',
                  style: TextStyle(fontSize: 16, color: scheme.onPrimary)),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            formatBRL(savings.amount),
            style: TextStyle(
              fontSize: 40,
              fontWeight: FontWeight.w900,
              color: scheme.onPrimary,
            ),
          ),
          Text(
            'comprando na ${savings.cheapest.name} em vez da loja mais cara.',
            style: TextStyle(
                fontSize: 14, color: scheme.onPrimary.withValues(alpha: 0.9)),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: Builder(
              builder: (btnContext) => FilledButton.tonalIcon(
                onPressed: listId == null
                    ? null
                    : () => shareSavings(
                          listId!,
                          savings.amount,
                          context: btnContext,
                        ),
                icon: const Icon(Icons.share),
                label: const Text('COMPARTILHAR ECONOMIA'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// App-bar brand title. Kept compact (small logo + smaller font, ellipsis) so
/// it fits between the back arrow and the map action on narrow phones.
class _AppBarTitle extends StatelessWidget {
  const _AppBarTitle();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Image.asset('assets/icon/logo.png', height: 22, width: 22),
        const SizedBox(width: 6),
        const Flexible(
          child: Text(
            'Compre Barato Alagoas',
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}

class _FreshnessLine extends StatelessWidget {
  const _FreshnessLine();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Row(
        children: [
          Icon(Icons.schedule, size: 16, color: Colors.black54),
          SizedBox(width: 6),
          Expanded(
            child: Text(
              'Cada preço mostra a data em que foi registrado.',
              style: TextStyle(fontSize: 13, color: Colors.black54),
            ),
          ),
        ],
      ),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({
    required this.icon,
    required this.text,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String text;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 64, color: Colors.black38),
            const SizedBox(height: 16),
            Text(text,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 18)),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 24),
              FilledButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}
