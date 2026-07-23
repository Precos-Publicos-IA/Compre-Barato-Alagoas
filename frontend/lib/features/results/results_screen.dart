import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format.dart';
import '../../core/layout.dart';
import '../../core/theme.dart';
import '../../data/models.dart';
import '../../data/providers.dart';
import '../map/map_screen.dart';
import '../share/share_service.dart';
import 'savings.dart';
import 'search_wait_copy.dart';
import 'store_card.dart';

class ResultsScreen extends ConsumerWidget {
  const ResultsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final result = ref.watch(searchControllerProvider);
    final basket = ref.watch(basketProvider);
    final status = ref.watch(searchStatusProvider);
    final busy = ref.watch(searchBusyProvider);
    final short = AppLayout.isShortHeight(context);
    final ctaH = AppLayout.ctaMinHeight(context);
    final barH = AppLayout.toolbarHeight(context);

    return Scaffold(
      appBar: AppBar(
        centerTitle: false,
        titleSpacing: 0,
        toolbarHeight: barH,
        title: const _AppBarTitle(),
        actions: [
          result.maybeWhen(
            data: (r) => (r != null && r.stores.isNotEmpty && !r.partial)
                ? IconButton(
                    icon: const Icon(Icons.map_outlined),
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
      body: AppLayout.constrainContent(
        context: context,
        child: result.when(
          loading: () => _LoadingProgress(
            status: status,
            wait: ref.watch(searchWaitSessionProvider),
            itemCount: basket.length,
          ),
          error: (e, _) => _Message(
            icon: Icons.error_outline_rounded,
            text: e.toString(),
            actionLabel: 'Tentar de novo',
            onAction: () =>
                ref.read(searchControllerProvider.notifier).run(basket),
          ),
          data: (r) {
            if (r == null) {
              if (busy) {
                return _LoadingProgress(
                  status: status,
                  wait: ref.watch(searchWaitSessionProvider),
                  itemCount: basket.length,
                );
              }
              return const _Message(
                icon: Icons.search_rounded,
                text: 'Faça uma busca.',
              );
            }
            if (r.stores.isEmpty) {
              if (busy) {
                return _LoadingProgress(
                  status: status,
                  wait: ref.watch(searchWaitSessionProvider),
                  itemCount: basket.length,
                );
              }
              return const _Message(
                icon: Icons.sentiment_dissatisfied_rounded,
                text: 'Nenhuma loja encontrada por perto.\n'
                    'Experimente termos comuns que as pessoas usam: '
                    '"pão francês", "arroz 5kg", "leite 1L", "feijão", "manteiga". '
                    'Evite marcas muito específicas no começo.',
              );
            }
            return _Results(
              response: r,
              items: basket,
              status: busy ? status : null,
              wait: busy ? ref.watch(searchWaitSessionProvider) : null,
            );
          },
        ),
      ),
      bottomNavigationBar: Material(
        elevation: 8,
        shadowColor: AppColors.shadow,
        color: AppColors.surface,
        child: SafeArea(
          child: AppLayout.constrainContent(
            context: context,
            expand: false,
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                short ? 10 : 16,
                short ? 8 : 10,
                short ? 10 : 16,
                short ? 8 : 12,
              ),
              child: FilledButton.icon(
                onPressed: () => Navigator.of(context).pop(),
                style: FilledButton.styleFrom(
                  minimumSize: Size.fromHeight(ctaH),
                  textStyle: TextStyle(
                    fontSize: short ? 16 : 17,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.4,
                  ),
                ),
                icon: Icon(Icons.edit_rounded, size: short ? 20 : 22),
                label: const Text('EDITAR LISTA'),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Results extends ConsumerWidget {
  const _Results({
    required this.response,
    required this.items,
    this.status,
    this.wait,
  });
  final SearchResponse response;
  final List<String> items;
  final String? status;
  final SearchWaitSession? wait;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final avoided = ref.watch(avoidedStoresProvider).asData?.value ?? const {};
    final favorites =
        ref.watch(favoriteStoresProvider).asData?.value ?? const {};

    final visible =
        response.stores.where((s) => !avoided.containsKey(s.cnpj)).toList();
    if (visible.isEmpty) {
      return const _Message(
        icon: Icons.visibility_off_outlined,
        text: 'Todas as lojas encontradas estão ocultas.\n'
            'Gerencie em "Minhas lojas".',
      );
    }

    final savings = computeSavings(visible);
    final coverage = computeCoverage(visible);
    final cheapest = savings?.cheapest ?? visible.first;
    final bestTotal = cheapest.total;
    final showPrimarySavings = shouldShowPrimarySavings(savings, coverage);

    final ordered = <StoreResult>[
      cheapest,
      ...visible.where(
          (s) => !identical(s, cheapest) && favorites.containsKey(s.cnpj)),
      ...visible.where(
          (s) => !identical(s, cheapest) && !favorites.containsKey(s.cnpj)),
    ];

    final rewrites = response.metrics.searchRewrites;
    final suggestions = response.metrics.suggestedRefinements;

    // PhoneLandscape: hide secondary banners so first store stays above fold.
    final short = AppLayout.isShortHeight(context);

    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: () => ref.read(searchControllerProvider.notifier).run(items),
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 16),
        children: [
          if (status != null || wait != null)
            _ProgressBanner(
              message: status,
              wait: wait,
              itemCount: items.length,
            ),
          // Coverage-first hero: never lead with “economize R$” on thin baskets.
          if (showPrimarySavings)
            _SavingsBanner(savings: savings!, listId: response.listId)
          else if (coverage.total > 0 && !coverage.isComplete)
            _PartialCoverageBanner(
              coverage: coverage,
              cheapestName: cheapest.name,
              listId: response.listId,
            ),
          _DisclaimerLine(text: response.dataDisclaimer),
          // On short landscape, skip rewrite/suggestion chrome entirely so the
          // winner card is visible (V-CLIP-TEXT residual).
          if (!short && rewrites.isNotEmpty) _RewriteBanner(rewrites: rewrites),
          if (!short && suggestions.isNotEmpty)
            _SuggestionsBanner(suggestions: suggestions),
          for (final store in ordered)
            StoreCard(
              store: store,
              isBest: identical(store, cheapest),
              deltaFromBest: store.total - bestTotal,
            ),
          if (!response.partial)
            _FeedbackCard(listId: response.listId, items: items),
        ],
      ),
    );
  }
}

/// Full-screen wait while SEFAZ/web prices are gathered (often minutes).
class _LoadingProgress extends StatefulWidget {
  const _LoadingProgress({
    this.status,
    this.wait,
    this.itemCount = 1,
  });
  final String? status;
  final SearchWaitSession? wait;
  final int itemCount;

  @override
  State<_LoadingProgress> createState() => _LoadingProgressState();
}

class _LoadingProgressState extends State<_LoadingProgress> {
  Timer? _timer;
  int _phraseIndex = 0;

  int get _etaMinutes =>
      widget.wait?.etaMinutes ?? estimateSearchEtaMinutes(widget.itemCount);

  bool get _canNotify => widget.wait?.notifyPromise ?? true;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(kSearchWaitPhrasePeriod, (_) {
      if (!mounted) return;
      setState(() => _phraseIndex++);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final phrase = searchWaitPhraseAt(_phraseIndex);
    final serverStatus = widget.status?.trim();
    final showServer = serverStatus != null &&
        serverStatus.isNotEmpty &&
        serverStatus != phrase;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: AppColors.primarySoft,
                borderRadius: BorderRadius.circular(20),
              ),
              padding: const EdgeInsets.all(18),
              child: const CircularProgressIndicator(strokeWidth: 3),
            ),
            const SizedBox(height: 20),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 350),
              child: Text(
                phrase,
                key: ValueKey<int>(_phraseIndex),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: AppColors.ink,
                    ),
              ),
            ),
            if (showServer) ...[
              const SizedBox(height: 6),
              Text(
                serverStatus,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.inkSecondary,
                      fontWeight: FontWeight.w600,
                    ),
              ),
            ],
            const SizedBox(height: 14),
            Text(
              searchWaitExplainer(etaMinutes: _etaMinutes),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.inkSecondary,
                    height: 1.4,
                  ),
            ),
            const SizedBox(height: 16),
            _EtaChip(etaMinutes: _etaMinutes),
            const SizedBox(height: 14),
            _NotifyPromiseCard(
              etaMinutes: _etaMinutes,
              canNotify: _canNotify,
            ),
            const SizedBox(height: 12),
            Text(
              'Os primeiros resultados aparecem assim que cada item for encontrado.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.inkMuted,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _EtaChip extends StatelessWidget {
  const _EtaChip({required this.etaMinutes});
  final int etaMinutes;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.accentSoft,
        borderRadius: BorderRadius.circular(AppRadii.pill),
        border: Border.all(color: AppColors.accent.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.schedule_rounded, size: 18, color: AppColors.ink),
          const SizedBox(width: 8),
          Text(
            'Tempo estimado: ~$etaMinutes min',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w800,
              color: AppColors.ink,
            ),
          ),
        ],
      ),
    );
  }
}

class _NotifyPromiseCard extends StatelessWidget {
  const _NotifyPromiseCard({
    required this.etaMinutes,
    required this.canNotify,
  });
  final int etaMinutes;
  final bool canNotify;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(color: AppColors.outline),
        boxShadow: appCardShadow(elevation: 0.35),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            canNotify
                ? Icons.notifications_active_outlined
                : Icons.notifications_none_rounded,
            color: AppColors.primaryDark,
            size: 22,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              searchWaitNotifyLine(
                etaMinutes: etaMinutes,
                canNotify: canNotify,
                isWeb: kIsWeb,
              ),
              style: const TextStyle(
                fontSize: 13.5,
                height: 1.35,
                color: AppColors.inkSecondary,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProgressBanner extends StatefulWidget {
  const _ProgressBanner({
    this.message,
    this.wait,
    this.itemCount = 1,
  });
  final String? message;
  final SearchWaitSession? wait;
  final int itemCount;

  @override
  State<_ProgressBanner> createState() => _ProgressBannerState();
}

class _ProgressBannerState extends State<_ProgressBanner> {
  Timer? _timer;
  int _phraseIndex = 0;

  int get _etaMinutes =>
      widget.wait?.etaMinutes ?? estimateSearchEtaMinutes(widget.itemCount);

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(kSearchWaitPhrasePeriod, (_) {
      if (!mounted) return;
      setState(() => _phraseIndex++);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final phrase = searchWaitPhraseAt(_phraseIndex);
    final server = widget.message?.trim();
    final line = (server != null && server.isNotEmpty) ? server : phrase;
    final canNotify = widget.wait?.notifyPromise ?? true;

    return Container(
      margin: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.primarySoft,
        borderRadius: BorderRadius.circular(AppRadii.sm),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.15)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2.2),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 280),
                  child: Text(
                    line,
                    key: ValueKey<String>(line),
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.primaryDark,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            canNotify
                ? 'Ainda reunindo dados · ~$_etaMinutes min · '
                    'avisamos por notificação ao terminar'
                : 'Ainda reunindo dados · tempo estimado ~$_etaMinutes min',
            style: const TextStyle(
              fontSize: 12.5,
              fontWeight: FontWeight.w600,
              color: AppColors.inkSecondary,
              height: 1.3,
            ),
          ),
        ],
      ),
    );
  }
}

class _DisclaimerLine extends StatelessWidget {
  const _DisclaimerLine({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    final short = AppLayout.isShortHeight(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(16, short ? 4 : 10, 16, short ? 2 : 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline_rounded,
              size: short ? 14 : 16, color: AppColors.inkMuted),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: short ? 11 : 12,
                color: AppColors.inkMuted,
              ),
              maxLines: short ? 1 : 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _RewriteBanner extends StatelessWidget {
  const _RewriteBanner({required this.rewrites});
  final List<SearchRewrite> rewrites;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.sm),
        border: Border.all(color: AppColors.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Como buscamos',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
          const SizedBox(height: 6),
          for (final r in rewrites.take(6))
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                '“${r.original}” → “${r.searchTerm}”',
                style: const TextStyle(fontSize: 13, color: AppColors.inkSecondary),
              ),
            ),
        ],
      ),
    );
  }
}

class _SuggestionsBanner extends StatelessWidget {
  const _SuggestionsBanner({required this.suggestions});
  final List<String> suggestions;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(AppRadii.sm),
        border: Border.all(color: AppColors.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Dicas para melhorar a busca',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
          const SizedBox(height: 6),
          for (final s in suggestions.take(4))
            Text('• $s',
                style: const TextStyle(fontSize: 13, color: AppColors.inkSecondary)),
        ],
      ),
    );
  }
}

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
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 12, 12, 4),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(color: AppColors.outline),
        boxShadow: appCardShadow(elevation: 0.4),
      ),
      child: _done
          ? const Row(
              children: [
                Icon(Icons.check_circle_rounded, color: AppColors.primary),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Obrigado pelo feedback!',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Este resultado foi útil?',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
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
    );
  }
}

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
          const Text(
            'Reportar item errado',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 12),
          if (widget.items.isNotEmpty)
            DropdownButtonFormField<String>(
              initialValue: _item,
              isExpanded: true,
              decoration: const InputDecoration(
                labelText: 'Qual item?',
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

/// Honest hero when basket coverage is incomplete / below savings threshold.
/// Copy-only: no big R$ claim so partial results are not sold as full wins.
class _PartialCoverageBanner extends StatelessWidget {
  const _PartialCoverageBanner({
    required this.coverage,
    required this.cheapestName,
    required this.listId,
  });
  final BasketCoverage coverage;
  final String cheapestName;
  final String? listId;

  @override
  Widget build(BuildContext context) {
    final short = AppLayout.isShortHeight(context);

    return Container(
      margin: EdgeInsets.fromLTRB(
        short ? 10 : 12,
        short ? 8 : 12,
        short ? 10 : 12,
        short ? 2 : 4,
      ),
      padding: EdgeInsets.all(short ? 12 : 16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(short ? AppRadii.sm : AppRadii.md),
        border: Border.all(color: AppColors.outline),
        boxShadow: appCardShadow(elevation: 0.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(
                Icons.inventory_2_outlined,
                color: AppColors.primaryDark,
                size: short ? 22 : 24,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  coverage.partialHeroTitle,
                  style: TextStyle(
                    fontSize: short ? 16 : 18,
                    fontWeight: FontWeight.w800,
                    color: AppColors.ink,
                    letterSpacing: -0.2,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          SizedBox(height: short ? 4 : 6),
          Text(
            coverage.partialHeroSubtitle,
            style: TextStyle(
              fontSize: short ? 12 : 13,
              color: AppColors.inkSecondary,
              height: 1.3,
            ),
          ),
          if (cheapestName.isNotEmpty) ...[
            SizedBox(height: short ? 2 : 4),
            Text(
              'Melhor parcial: $cheapestName',
              style: TextStyle(
                fontSize: short ? 12 : 13,
                fontWeight: FontWeight.w600,
                color: AppColors.primaryDark,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          // Share without claiming a R$ savings amount (partial basket).
          if (listId != null) ...[
            SizedBox(height: short ? 8 : 12),
            SizedBox(
              height: short ? 40 : 48,
              child: Builder(
                builder: (btnContext) => OutlinedButton.icon(
                  onPressed: () => shareSavings(
                    listId!,
                    0,
                    context: btnContext,
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.primaryDark,
                    side: const BorderSide(color: AppColors.outline),
                    textStyle: TextStyle(
                      fontSize: short ? 13 : 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  icon: Icon(Icons.share_rounded, size: short ? 18 : 20),
                  label: const Text('COMPARTILHAR BUSCA'),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Savings hero — deliberately big. Dense row on PhoneLandscape.
/// Only shown when [shouldShowPrimarySavings] is true (coverage gate).
class _SavingsBanner extends StatelessWidget {
  const _SavingsBanner({required this.savings, required this.listId});
  final SavingsInfo savings;
  final String? listId;

  @override
  Widget build(BuildContext context) {
    final short = AppLayout.isShortHeight(context);

    if (short) {
      return Container(
        margin: const EdgeInsets.fromLTRB(10, 8, 10, 2),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.primaryDark, AppColors.primaryMid],
          ),
          borderRadius: BorderRadius.circular(AppRadii.sm),
          boxShadow: appCardShadow(elevation: 0.8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(Icons.savings_rounded, color: Colors.white, size: 22),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Economize até ${formatBRL(savings.amount)}',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                      letterSpacing: -0.3,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 2),
            Text(
              'na ${savings.cheapest.name} vs. a loja mais cara.',
              style: TextStyle(
                fontSize: 12,
                color: Colors.white.withValues(alpha: 0.9),
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 40,
              child: Builder(
                builder: (btnContext) => FilledButton.tonalIcon(
                  onPressed: listId == null
                      ? null
                      : () => shareSavings(
                            listId!,
                            savings.amount,
                            context: btnContext,
                          ),
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: AppColors.primaryDark,
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    textStyle: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  icon: const Icon(Icons.share_rounded, size: 18),
                  label: const Text('COMPARTILHAR ECONOMIA'),
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.fromLTRB(12, 12, 12, 4),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.primaryDark, AppColors.primary, AppColors.primaryMid],
        ),
        borderRadius: BorderRadius.circular(AppRadii.lg),
        boxShadow: appCardShadow(elevation: 1.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.savings_rounded,
                    color: Colors.white, size: 22),
              ),
              const SizedBox(width: 10),
              Text(
                'Você pode economizar até',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: Colors.white.withValues(alpha: 0.95),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            formatBRL(savings.amount),
            style: const TextStyle(
              fontSize: 40,
              fontWeight: FontWeight.w900,
              color: Colors.white,
              letterSpacing: -1,
              height: 1.05,
            ),
          ),
          Text(
            'comprando na ${savings.cheapest.name} em vez da loja mais cara.',
            style: TextStyle(
              fontSize: 14,
              color: Colors.white.withValues(alpha: 0.9),
            ),
          ),
          const SizedBox(height: 14),
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
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: AppColors.primaryDark,
                  minimumSize: const Size.fromHeight(48),
                  textStyle: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                icon: const Icon(Icons.share_rounded),
                label: const Text('COMPARTILHAR ECONOMIA'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AppBarTitle extends StatelessWidget {
  const _AppBarTitle();

  @override
  Widget build(BuildContext context) {
    final short = AppLayout.isShortHeight(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: AppColors.primarySoft,
            borderRadius: BorderRadius.circular(8),
          ),
          padding: const EdgeInsets.all(3),
          child: Image.asset('assets/icon/logo.png', fit: BoxFit.contain),
        ),
        const SizedBox(width: 8),
        Flexible(
          child: Text(
            short ? 'Compre Barato' : 'Compre Barato Alagoas',
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.2,
              color: AppColors.ink,
            ),
          ),
        ),
      ],
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
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: AppColors.surfaceMuted,
                borderRadius: BorderRadius.circular(24),
              ),
              child: Icon(icon, size: 40, color: AppColors.inkMuted),
            ),
            const SizedBox(height: 18),
            Text(
              text,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: AppColors.inkSecondary,
                    height: 1.4,
                  ),
            ),
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
