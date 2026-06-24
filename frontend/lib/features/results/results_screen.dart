import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format.dart';
import '../../data/models.dart';
import '../../data/providers.dart';
import '../map/map_screen.dart';
import '../settings/settings_sheet.dart';
import '../share/share_service.dart';
import '../stores/store_prefs_sheet.dart';
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
            return _EmptyResults(basket: basket);
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
    );
  }
}

/// Empty-results with actionable CTAs (issue #297): widen radius/days, clear
/// avoided stores, open settings, or retry search.
class _EmptyResults extends ConsumerWidget {
  const _EmptyResults({required this.basket});
  final List<String> basket;

  Future<void> _widenAndRetry(WidgetRef ref, {int? addKm, int? addDays}) async {
    final prefs = ref.read(searchPrefsProvider).asData?.value;
    final curR = prefs?.radiusKm ?? 8;
    final curD = prefs?.days ?? 7;
    if (addKm != null) {
      await ref.read(searchPrefsProvider.notifier).setRadius(curR + addKm);
    }
    if (addDays != null) {
      await ref.read(searchPrefsProvider.notifier).setDays(curD + addDays);
    }
    await ref.read(searchControllerProvider.notifier).run(basket);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final params = ref.watch(searchPrefsProvider).asData?.value;
    final radius = params?.radiusKm ?? 8;
    final days = params?.days ?? 7;
    final avoided = ref.watch(avoidedStoresProvider).asData?.value ?? const {};
    final hasAvoided = avoided.isNotEmpty;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.sentiment_dissatisfied,
                size: 64, color: Colors.black38),
            const SizedBox(height: 16),
            const Text(
              'Nenhuma loja encontrada por perto.\n'
              'Experimente termos comuns: "pão francês", "arroz 5kg", '
              '"leite 1L", "feijão", "manteiga". Evite marcas muito específicas.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18),
            ),
            const SizedBox(height: 8),
            Text(
              'Busca atual: até $radius km · últimos $days dias'
              '${hasAvoided ? ' · ${avoided.length} loja(s) oculta(s)' : ''}',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13, color: Colors.black54),
            ),
            const SizedBox(height: 20),
            if (radius < 15)
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () => _widenAndRetry(ref, addKm: 4),
                  icon: const Icon(Icons.social_distance),
                  label: Text(
                      'Aumentar distância (${radius}→${(radius + 4).clamp(1, 15)} km) e buscar'),
                ),
              ),
            if (radius < 15) const SizedBox(height: 8),
            if (days < 30)
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () => _widenAndRetry(ref, addDays: 7),
                  icon: const Icon(Icons.calendar_month),
                  label: Text(
                      'Incluir preços mais antigos (${days}→${(days + 7).clamp(1, 30)} dias)'),
                ),
              ),
            if (days < 30) const SizedBox(height: 8),
            if (hasAvoided)
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () async {
                    final n = ref.read(avoidedStoresProvider.notifier);
                    for (final cnpj in avoided.keys.toList()) {
                      await n.remove(cnpj);
                    }
                    await ref
                        .read(searchControllerProvider.notifier)
                        .run(basket);
                  },
                  icon: const Icon(Icons.visibility),
                  label: Text(
                      'Mostrar lojas ocultas de novo (${avoided.length}) e buscar'),
                ),
              ),
            if (hasAvoided) const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: TextButton.icon(
                onPressed: () => SettingsSheet.show(context),
                icon: const Icon(Icons.tune),
                label: const Text('Abrir configurações de busca'),
              ),
            ),
            if (hasAvoided)
              TextButton.icon(
                onPressed: () => StorePrefsSheet.show(context),
                icon: const Icon(Icons.storefront),
                label: const Text('Gerenciar lojas ocultas'),
              ),
            TextButton.icon(
              onPressed: () =>
                  ref.read(searchControllerProvider.notifier).run(basket),
              icon: const Icon(Icons.refresh),
              label: const Text('Tentar de novo sem mudar filtros'),
            ),
          ],
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
          _MissingItemsBanner(stores: visible, items: items),
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

/// Results-level summary when some basket lines are missing at stores (#298).
class _MissingItemsBanner extends StatelessWidget {
  const _MissingItemsBanner({required this.stores, required this.items});
  final List<StoreResult> stores;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    if (stores.isEmpty || items.isEmpty) return const SizedBox.shrink();

    // Items missing at *every* visible store (or at least at cheapest incomplete).
    final alwaysMissing = <String>{};
    final anyMissing = <String>{};
    for (final it in items) {
      var missCount = 0;
      for (final s in stores) {
        if (s.missing.any((m) =>
            m.toLowerCase().trim() == it.toLowerCase().trim() ||
            s.missing.contains(it))) {
          missCount++;
          anyMissing.add(it);
        } else if (s.missing.isNotEmpty) {
          // also count fuzzy: store.missing strings may not equal basket lines
          for (final m in s.missing) {
            anyMissing.add(m);
          }
        }
      }
      if (missCount == stores.length) alwaysMissing.add(it);
    }
    // Prefer server-reported missing strings across stores.
    for (final s in stores) {
      for (final m in s.missing) {
        anyMissing.add(m);
      }
    }
    if (anyMissing.isEmpty) return const SizedBox.shrink();

    final incompleteStores =
        stores.where((s) => s.missing.isNotEmpty).length;
    final sample = anyMissing.take(4).join(', ');
    final more = anyMissing.length > 4 ? ' (+${anyMissing.length - 4})' : '';

    return Card(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      color: Colors.amber.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.warning_amber_rounded,
                color: Colors.amber.shade900, size: 28),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    incompleteStores == stores.length
                        ? 'Nenhuma loja tem a lista completa'
                        : '$incompleteStores de ${stores.length} lojas com itens em falta',
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Itens sem preço em alguma loja: $sample$more. '
                    'Totais comparam só o que cada loja conseguiu montar — refine termos ou remova itens raros.',
                    style: const TextStyle(fontSize: 13, color: Colors.black87),
                  ),
                ],
              ),
            ),
          ],
        ),
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
