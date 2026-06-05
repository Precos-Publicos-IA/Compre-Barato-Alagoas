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

    return Scaffold(
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
                      MaterialPageRoute(builder: (_) => MapScreen(response: r)),
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
                  'Tente mudar os itens da sua lista.',
            );
          }
          return _Results(response: r);
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
    );
  }
}

class _Results extends StatelessWidget {
  const _Results({required this.response});
  final SearchResponse response;

  @override
  Widget build(BuildContext context) {
    final stores = response.stores;
    final savings = computeSavings(stores);
    final bestTotal = savings?.cheapest.total ?? stores.first.total;

    return ListView(
      padding: const EdgeInsets.only(bottom: 16),
      children: [
        if (savings != null && savings.amount > 0)
          _SavingsBanner(savings: savings, listId: response.listId),
        const _FreshnessLine(),
        for (var i = 0; i < stores.length; i++)
          StoreCard(
            store: stores[i],
            isBest: identical(stores[i], savings?.cheapest) ||
                (savings == null && i == 0),
            deltaFromBest: stores[i].total - bestTotal,
          ),
      ],
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
            child: FilledButton.tonalIcon(
              onPressed:
                  listId == null ? null : () => shareSavings(listId!, savings.amount),
              icon: const Icon(Icons.share),
              label: const Text('COMPARTILHAR ECONOMIA'),
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
