import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/layout.dart';
import '../../core/staple_icons.dart';
import '../../core/theme.dart';
import '../../data/models.dart';
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
          _addCurrent();
          setState(() => _listening = false);
        }
      },
    );
    if (!ok) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Voz indisponível neste aparelho (microfone ou reconhecimento '
              'de fala). Digite o item ou tente outro idioma nas ajustes do sistema.',
            ),
          ),
        );
      }
      return;
    }
    setState(() => _listening = true);
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
    final short = AppLayout.isShortHeight(context);
    final phoneLand = AppLayout.isPhoneLandscape(context);
    final pad = AppLayout.pagePadding(context);
    final ctaH = AppLayout.ctaMinHeight(context);
    final barH = AppLayout.toolbarHeight(context);

    return Scaffold(
      appBar: AppBar(
        centerTitle: true,
        toolbarHeight: barH,
        actions: [
          IconButton(
            tooltip: 'Salvar listas na nuvem',
            icon: Icon(
              cloudOn ? Icons.cloud_done_rounded : Icons.cloud_outlined,
              size: short ? 22 : 24,
            ),
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
                  leading: Icon(Icons.storefront_outlined),
                  title: Text('Minhas lojas'),
                ),
              ),
              PopupMenuItem(
                value: 'settings',
                child: ListTile(
                  leading: Icon(Icons.settings_outlined),
                  title: Text('Configurações'),
                ),
              ),
            ],
          ),
        ],
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: short ? 28 : 34,
              height: short ? 28 : 34,
              decoration: BoxDecoration(
                color: AppColors.primarySoft,
                borderRadius: BorderRadius.circular(10),
              ),
              padding: const EdgeInsets.all(4),
              child: Image.asset(
                'assets/icon/logo.png',
                fit: BoxFit.contain,
              ),
            ),
            SizedBox(width: short ? 8 : 10),
            Flexible(
              child: Text(
                short ? 'Compre Barato' : 'Compre Barato Alagoas',
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: short ? 16 : 17,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.3,
                  color: AppColors.ink,
                ),
              ),
            ),
          ],
        ),
      ),
      body: SafeArea(
        child: AppLayout.constrainContent(
          context: context,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final desktop4k = AppLayout.isDesktop4k(context);
              final shellPad = desktop4k
                  ? (constraints.maxWidth >= 1400 ? 36.0 : 28.0)
                  : pad;
              final form = SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(
                  shellPad,
                  desktop4k ? shellPad - 4 : (short ? 4 : 8),
                  shellPad,
                  shellPad,
                ),
                child: _HomeFormColumn(
                  short: short,
                  phoneLand: phoneLand,
                  desktop4k: desktop4k,
                  basket: basket,
                  suggestions: suggestions,
                  controller: _controller,
                  listening: _listening,
                  onSubmit: _addCurrent,
                  onMic: _toggleVoice,
                  onAdd: _addCurrent,
                  onPickStaple: (label) {
                    ref.read(basketProvider.notifier).add(label);
                    _dismissKeyboard();
                  },
                  onClearBasket: () =>
                      ref.read(basketProvider.notifier).clear(),
                ),
              );

              if (!desktop4k) return form;

              // Wide desktop: elevated product shell so QHD/4K reads as a
              // comfortable centered column (V-FORM-FACTOR).
              return Padding(
                padding: EdgeInsets.fromLTRB(shellPad * 0.65, 28, shellPad * 0.65, 12),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(AppRadii.xl),
                    boxShadow: appCardShadow(elevation: 1.6),
                    border: Border.all(color: AppColors.outline),
                  ),
                  child: form,
                ),
              );
            },
          ),
        ),
      ),
      bottomNavigationBar: _BottomCtaBar(
        height: ctaH,
        short: short,
        enabled: basket.isNotEmpty,
        onPressed: _goToResults,
        count: basket.length,
      ),
    );
  }
}

/// Elevated search field with integrated mic + add — not a bare OutlineInput.
/// Shared home form body (search + staples + basket).
class _HomeFormColumn extends StatelessWidget {
  const _HomeFormColumn({
    required this.short,
    required this.phoneLand,
    required this.desktop4k,
    required this.basket,
    required this.suggestions,
    required this.controller,
    required this.listening,
    required this.onSubmit,
    required this.onMic,
    required this.onAdd,
    required this.onPickStaple,
    required this.onClearBasket,
  });

  final bool short;
  final bool phoneLand;
  final bool desktop4k;
  final List<String> basket;
  final AsyncValue<List<Suggestion>> suggestions;
  final TextEditingController controller;
  final bool listening;
  final VoidCallback onSubmit;
  final VoidCallback onMic;
  final VoidCallback onAdd;
  final ValueChanged<String> onPickStaple;
  final VoidCallback onClearBasket;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (!phoneLand) ApkBanner(compact: short),
        if (!short) ...[
          Text(
            'O que você precisa comprar?',
            style: desktop4k
                ? Theme.of(context)
                    .textTheme
                    .headlineMedium
                    ?.copyWith(fontWeight: FontWeight.w800)
                : Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          Text(
            'Compare preços de mercados em Alagoas e economize.',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: AppColors.inkMuted,
                  fontSize: desktop4k ? 17 : null,
                ),
          ),
          SizedBox(height: desktop4k ? 22 : 14),
        ] else ...[
          Text(
            'Monte sua lista',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 6),
        ],
        _SearchField(
          controller: controller,
          listening: listening,
          compact: short,
          onSubmit: onSubmit,
          onMic: onMic,
          onAdd: onAdd,
        ),
        SizedBox(height: short ? 8 : 14),
        suggestions.when(
          data: (items) {
            if (items.isEmpty) return const SizedBox.shrink();
            return _StapleSection(
              items: items,
              compact: short,
              desktop4k: desktop4k,
              onPick: onPickStaple,
            );
          },
          loading: () => const SizedBox.shrink(),
          error: (_, _) => const SizedBox.shrink(),
        ),
        if (basket.isEmpty) _RecentLists(compact: short),
        if (desktop4k && basket.isEmpty) ...[
          const SizedBox(height: 28),
          const _DesktopTipsCard(),
        ],
        if (basket.isNotEmpty) ...[
          SizedBox(height: short ? 10 : 18),
          Row(
            children: [
              Text(
                'Sua lista (${basket.length})',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const Spacer(),
              TextButton(
                onPressed: onClearBasket,
                style: TextButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  foregroundColor: AppColors.inkMuted,
                ),
                child: const Text('Limpar'),
              ),
            ],
          ),
          SizedBox(height: short ? 4 : 8),
          _BasketList(items: basket, compact: short),
        ],
      ],
    );
  }
}

class _SearchField extends StatelessWidget {
  const _SearchField({
    required this.controller,
    required this.listening,
    required this.compact,
    required this.onSubmit,
    required this.onMic,
    required this.onAdd,
  });

  final TextEditingController controller;
  final bool listening;
  final bool compact;
  final VoidCallback onSubmit;
  final VoidCallback onMic;
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    final fieldH = compact ? 48.0 : 56.0;
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        boxShadow: appCardShadow(elevation: 0.8),
        border: Border.all(color: AppColors.outline),
      ),
      padding: EdgeInsets.fromLTRB(compact ? 8 : 10, 6, 6, 6),
      child: Row(
        children: [
          Icon(
            Icons.search_rounded,
            color: AppColors.inkMuted,
            size: compact ? 22 : 24,
          ),
          const SizedBox(width: 6),
          Expanded(
            child: SizedBox(
              height: fieldH,
              child: TextField(
                controller: controller,
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => onSubmit(),
                style: TextStyle(
                  fontSize: compact ? 16 : 17,
                  fontWeight: FontWeight.w500,
                  color: AppColors.ink,
                ),
                decoration: InputDecoration(
                  hintText: compact
                      ? 'arroz, feijão, leite…'
                      : 'Ex.: arroz, feijão, leite',
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  filled: false,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 4,
                    vertical: compact ? 10 : 14,
                  ),
                  isDense: compact,
                ),
              ),
            ),
          ),
          _RoundIconBtn(
            tooltip: 'Adicionar',
            icon: Icons.add_rounded,
            onTap: onAdd,
            compact: compact,
            filled: false,
          ),
          const SizedBox(width: 4),
          _RoundIconBtn(
            tooltip: listening ? 'Parar gravação' : 'Falar item',
            icon: listening ? Icons.stop : Icons.mic,
            onTap: onMic,
            compact: compact,
            filled: true,
            danger: listening,
          ),
        ],
      ),
    );
  }
}

class _RoundIconBtn extends StatelessWidget {
  const _RoundIconBtn({
    required this.tooltip,
    required this.icon,
    required this.onTap,
    required this.compact,
    required this.filled,
    this.danger = false,
  });

  final String tooltip;
  final IconData icon;
  final VoidCallback onTap;
  final bool compact;
  final bool filled;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final size = compact ? 44.0 : 48.0;
    final bg = !filled
        ? AppColors.surfaceMuted
        : (danger ? AppColors.danger : AppColors.primary);
    final fg = filled ? Colors.white : AppColors.primary;
    return Semantics(
      button: true,
      label: tooltip,
      child: Tooltip(
        message: tooltip,
        child: Material(
          color: bg,
          shape: const CircleBorder(),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: onTap,
            child: SizedBox(
              width: size,
              height: size,
              child: Icon(icon, color: fg, size: compact ? 22 : 24),
            ),
          ),
        ),
      ),
    );
  }
}

class _StapleSection extends StatelessWidget {
  const _StapleSection({
    required this.items,
    required this.compact,
    required this.desktop4k,
    required this.onPick,
  });

  final List<Suggestion> items;
  final bool compact;
  final bool desktop4k;
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!compact)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Text(
              'Itens do dia a dia',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.inkMuted,
                    letterSpacing: 0.2,
                  ),
            ),
          ),
        if (compact)
          SizedBox(
            height: 44,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: items.length,
              separatorBuilder: (_, _) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                final s = items[i];
                return _StapleChip(
                  label: s.label,
                  onTap: () => onPick(s.label),
                  compact: true,
                );
              },
            ),
          )
        else
          Wrap(
            spacing: desktop4k ? 10 : 8,
            runSpacing: desktop4k ? 10 : 8,
            children: [
              for (final s in items)
                _StapleChip(
                  label: s.label,
                  onTap: () => onPick(s.label),
                  compact: false,
                ),
            ],
          ),
      ],
    );
  }
}

/// Staple as icon+label tile — Material icons, never emoji tofu.
class _StapleChip extends StatelessWidget {
  const _StapleChip({
    required this.label,
    required this.onTap,
    required this.compact,
  });

  final String label;
  final VoidCallback onTap;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final icon = stapleIconFor(label);
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadii.sm),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadii.sm),
        child: Container(
          constraints: BoxConstraints(
            minHeight: compact ? 40 : 48,
            minWidth: compact ? 0 : 96,
          ),
          padding: EdgeInsets.symmetric(
            horizontal: compact ? 12 : 12,
            vertical: compact ? 8 : 10,
          ),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadii.sm),
            border: Border.all(color: AppColors.outline),
            boxShadow: appCardShadow(elevation: 0.4),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: compact ? 26 : 30,
                height: compact ? 26 : 30,
                decoration: BoxDecoration(
                  color: AppColors.primarySoft,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  icon,
                  size: compact ? 16 : 18,
                  color: AppColors.primary,
                ),
              ),
              SizedBox(width: compact ? 8 : 8),
              Text(
                label,
                style: TextStyle(
                  fontSize: compact ? 14 : 15,
                  fontWeight: FontWeight.w600,
                  color: AppColors.ink,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BasketList extends ConsumerWidget {
  const _BasketList({required this.items, required this.compact});
  final List<String> items;
  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        for (var i = 0; i < items.length; i++)
          Container(
            margin: EdgeInsets.only(bottom: compact ? 6 : 8),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(AppRadii.sm),
              border: Border.all(color: AppColors.outline),
              boxShadow: appCardShadow(elevation: 0.35),
            ),
            child: ListTile(
              dense: compact,
              contentPadding: EdgeInsets.only(
                left: compact ? 12 : 14,
                right: 4,
              ),
              leading: Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.primarySoft,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  stapleIconFor(items[i]),
                  size: 18,
                  color: AppColors.primary,
                ),
              ),
              title: Text(
                items[i],
                style: TextStyle(
                  fontSize: compact ? 16 : 17,
                  fontWeight: FontWeight.w600,
                ),
              ),
              trailing: IconButton(
                icon: const Icon(Icons.close_rounded),
                tooltip: 'Remover',
                onPressed: () =>
                    ref.read(basketProvider.notifier).removeAt(i),
              ),
            ),
          ),
      ],
    );
  }
}

class _BottomCtaBar extends StatelessWidget {
  const _BottomCtaBar({
    required this.height,
    required this.short,
    required this.enabled,
    required this.onPressed,
    required this.count,
  });

  final double height;
  final bool short;
  final bool enabled;
  final VoidCallback onPressed;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Material(
      elevation: 8,
      shadowColor: AppColors.shadow,
      color: AppColors.surface,
      child: SafeArea(
        child: AppLayout.constrainContent(
          context: context,
          child: Padding(
            padding: EdgeInsets.fromLTRB(
              short ? 10 : 16,
              short ? 8 : 10,
              short ? 10 : 16,
              short ? 8 : 12,
            ),
            child: FilledButton(
              onPressed: onPressed,
              style: FilledButton.styleFrom(
                minimumSize: Size.fromHeight(height),
                backgroundColor:
                    enabled ? AppColors.primary : AppColors.outline,
                foregroundColor:
                    enabled ? Colors.white : AppColors.inkMuted,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadii.md),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.price_check_rounded, size: short ? 22 : 24),
                  const SizedBox(width: 10),
                  Text(
                    'VER PREÇOS',
                    style: TextStyle(
                      fontSize: short ? 16 : 17,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.6,
                    ),
                  ),
                  if (count > 0) ...[
                    const SizedBox(width: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.22),
                        borderRadius: BorderRadius.circular(AppRadii.pill),
                      ),
                      child: Text(
                        '$count',
                        style: TextStyle(
                          fontSize: short ? 13 : 14,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DesktopTipsCard extends StatelessWidget {
  const _DesktopTipsCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(22, 22, 22, 20),
      decoration: BoxDecoration(
        color: AppColors.primarySoft.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(AppRadii.lg),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.15)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.lightbulb_outline_rounded,
                  color: AppColors.primary, size: 28),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Como economizar em Alagoas',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            '• Toque nos itens rápidos (arroz, feijão, leite…) ou digite sua lista.\n'
            '• Compare preços de vendas recentes (NFC-e) nas lojas perto de você.\n'
            '• Compartilhe a economia com a família e veja o mapa das lojas.',
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  height: 1.55,
                  color: AppColors.inkSecondary,
                ),
          ),
        ],
      ),
    );
  }
}

class _RecentLists extends ConsumerWidget {
  const _RecentLists({this.compact = false});
  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recents = ref.watch(recentListsProvider);
    return recents.maybeWhen(
      data: (lists) {
        if (lists.isEmpty) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(height: compact ? 10 : 18),
            Text(
              'Listas recentes',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.inkMuted,
                  ),
            ),
            SizedBox(height: compact ? 6 : 8),
            for (final list in lists)
              Container(
                margin: EdgeInsets.only(bottom: compact ? 6 : 8),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppRadii.sm),
                  border: Border.all(color: AppColors.outline),
                ),
                child: ListTile(
                  dense: compact,
                  leading: Icon(
                    Icons.history_rounded,
                    color: AppColors.primary,
                    size: compact ? 22 : 24,
                  ),
                  title: Text(
                    list.join(', '),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: compact ? 14 : 15,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  trailing: Icon(
                    Icons.replay_rounded,
                    color: AppColors.inkMuted,
                    size: compact ? 20 : 22,
                  ),
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
