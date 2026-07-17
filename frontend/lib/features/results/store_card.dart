import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format.dart';
import '../../core/layout.dart';
import '../../core/theme.dart';
import '../../data/models.dart';
import '../../data/providers.dart';
import 'store_actions.dart';

/// One store in the vertical results list.
/// Cheapest store: gold accent + "MAIS BARATO" badge + starts expanded.
class StoreCard extends ConsumerStatefulWidget {
  const StoreCard({
    super.key,
    required this.store,
    required this.isBest,
    required this.deltaFromBest,
  });

  final StoreResult store;
  final bool isBest;
  final double deltaFromBest;

  @override
  ConsumerState<StoreCard> createState() => _StoreCardState();
}

class _StoreCardState extends ConsumerState<StoreCard> {
  late bool _expanded = widget.isBest;

  void _toggleFavorite(bool isFav) {
    final store = widget.store;
    if (isFav) {
      ref.read(favoriteStoresProvider.notifier).remove(store.cnpj);
    } else {
      ref.read(favoriteStoresProvider.notifier).add(store.cnpj, store.name);
      ref.read(avoidedStoresProvider.notifier).remove(store.cnpj);
    }
  }

  Future<void> _hide() async {
    final store = widget.store;
    final avoided = ref.read(avoidedStoresProvider.notifier);
    await ref.read(favoriteStoresProvider.notifier).remove(store.cnpj);
    await avoided.add(store.cnpj, store.name);
    ref.read(searchControllerProvider.notifier).run(ref.read(basketProvider));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('${store.name} ocultada'),
        action: SnackBarAction(
          label: 'DESFAZER',
          onPressed: () {
            avoided.remove(store.cnpj);
            ref
                .read(searchControllerProvider.notifier)
                .run(ref.read(basketProvider));
          },
        ),
      ),
    );
  }

  String _priceDetail(ItemOffer it) {
    final bits = <String>[];
    if (it.packageLabel != null && it.packageLabel!.isNotEmpty) {
      bits.add(it.packageLabel!);
    }
    if (it.quantityParsed && it.unitPrice != null && it.baseUnit != null) {
      if (it.baseUnit == 'un') {
        if ((it.quantity ?? 1) > 1) {
          bits.add('${formatBRL(it.unitPrice!)} cada');
        }
      } else {
        bits.add(formatUnitPrice(it.unitPrice!, it.baseUnit!));
      }
    }
    return bits.join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final store = widget.store;
    final isFav = ref
            .watch(favoriteStoresProvider)
            .asData
            ?.value
            .containsKey(store.cnpj) ??
        false;
    final short = AppLayout.isShortHeight(context);
    final isBest = widget.isBest;

    return Container(
      margin: EdgeInsets.symmetric(
        horizontal: short ? 10 : 12,
        vertical: short ? 4 : 6,
      ),
      decoration: BoxDecoration(
        color: isBest ? AppColors.primaryContainer : AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(
          color: isBest ? AppColors.primary.withValues(alpha: 0.45) : AppColors.outline,
          width: isBest ? 1.6 : 1,
        ),
        boxShadow: appCardShadow(elevation: isBest ? 1.1 : 0.5),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (isBest)
            Container(
              height: 4,
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [AppColors.accent, AppColors.primaryMid],
                ),
              ),
            ),
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                14,
                short ? 10 : 14,
                10,
                short ? 10 : 14,
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (isBest) const _BestBadge(),
                        Row(
                          children: [
                            if (isFav) ...[
                              const Icon(Icons.star_rounded,
                                  size: 18, color: AppColors.accent),
                              const SizedBox(width: 4),
                            ],
                            Flexible(
                              child: Text(
                                store.name,
                                style: Theme.of(context)
                                    .textTheme
                                    .titleLarge
                                    ?.copyWith(
                                      fontSize: short ? 16 : 18,
                                      fontWeight: FontWeight.w800,
                                    ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 3),
                        Text(
                          [
                            if (store.distanceKm != null)
                              formatDistance(store.distanceKm),
                            '${store.itemsFound} de ${store.itemsTotal} itens',
                          ].join(' · '),
                          style: TextStyle(
                            fontSize: short ? 12 : 13,
                            color: AppColors.inkMuted,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        if (store.rankReason != null &&
                            store.rankReason!.isNotEmpty) ...[
                          const SizedBox(height: 3),
                          Text(
                            store.rankReason!,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: isBest
                                  ? AppColors.primary
                                  : AppColors.inkSecondary,
                            ),
                          ),
                        ],
                        if (store.missing.isNotEmpty && !_expanded) ...[
                          const SizedBox(height: 4),
                          Text(
                            store.missing.length == 1
                                ? 'Falta: ${store.missing.first}'
                                : 'Faltam: ${store.missing.join(", ")}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.danger,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        formatBRL(store.total),
                        style: TextStyle(
                          fontSize: short ? 22 : 26,
                          fontWeight: FontWeight.w900,
                          letterSpacing: -0.5,
                          color: isBest ? AppColors.primary : AppColors.ink,
                        ),
                      ),
                      if (widget.deltaFromBest > 0)
                        Container(
                          margin: const EdgeInsets.only(top: 2),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.dangerSoft,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            '+${formatBRL(widget.deltaFromBest)}',
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: AppColors.danger,
                            ),
                          ),
                        ),
                      Icon(
                        _expanded
                            ? Icons.expand_less_rounded
                            : Icons.expand_more_rounded,
                        color: AppColors.inkMuted,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[
            Divider(height: 1, color: AppColors.outline.withValues(alpha: 0.8)),
            Padding(
              padding: EdgeInsets.fromLTRB(14, short ? 6 : 10, 14, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (store.address != null) ...[
                    Row(
                      children: [
                        const Icon(Icons.place_outlined,
                            size: 16, color: AppColors.inkMuted),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            store.address!,
                            style: const TextStyle(
                              fontSize: 13,
                              color: AppColors.inkMuted,
                            ),
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: short ? 6 : 8),
                  ],
                  for (final it in store.items) _itemRow(it, short),
                  if (store.missing.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    const Text(
                      'Não encontrado nesta loja:',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        for (final m in store.missing)
                          Chip(
                            label: Text(
                              m,
                              style: const TextStyle(fontSize: 13),
                            ),
                            backgroundColor: AppColors.dangerSoft,
                            side: BorderSide.none,
                            visualDensity: VisualDensity.compact,
                          ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _ActionBtn(
                        icon: Icons.map_outlined,
                        label: 'Mapa',
                        onTap: () => StoreActions.openMaps(store),
                      ),
                      _ActionBtn(
                        icon: Icons.local_taxi_outlined,
                        label: 'Uber',
                        onTap: () => StoreActions.openUber(store),
                      ),
                      _ActionBtn(
                        icon: Icons.directions_car_outlined,
                        label: '99',
                        onTap: () => StoreActions.open99(store),
                      ),
                      _ActionBtn(
                        icon: Icons.copy_rounded,
                        label: 'Endereço',
                        onTap: () => StoreActions.copyAddress(context, store),
                      ),
                    ],
                  ),
                  Divider(
                    height: 16,
                    color: AppColors.outline.withValues(alpha: 0.8),
                  ),
                  Row(
                    children: [
                      _ActionBtn(
                        icon: isFav ? Icons.star_rounded : Icons.star_outline_rounded,
                        label: isFav ? 'Favorita' : 'Favoritar',
                        onTap: () => _toggleFavorite(isFav),
                      ),
                      _ActionBtn(
                        icon: Icons.visibility_off_outlined,
                        label: 'Ocultar',
                        onTap: _hide,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _itemRow(ItemOffer it, bool short) {
    final detail = _priceDetail(it);
    final date = formatDate(it.saleDate);
    return Padding(
      padding: EdgeInsets.symmetric(vertical: short ? 5 : 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  it.description ?? it.query,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.ink,
                  ),
                ),
                if (it.isBestMatch)
                  const Text(
                    'Melhor opção nesta loja',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: AppColors.inkMuted,
                    ),
                  ),
                if (detail.isNotEmpty)
                  Text(
                    detail,
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.inkMuted,
                    ),
                  ),
                if (date.isNotEmpty)
                  Row(
                    children: [
                      const Icon(Icons.schedule_rounded,
                          size: 12, color: AppColors.inkMuted),
                      const SizedBox(width: 3),
                      Text(
                        'preço de $date',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.inkMuted,
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                _lineFigure(it),
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: AppColors.ink,
                ),
              ),
              if (it.requestedQuantity > 1 && it.price != null)
                Text(
                  '${it.requestedQuantity} × ${formatBRL(it.price!)}',
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.inkMuted,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  String _lineFigure(ItemOffer it) {
    final value = it.lineTotal ?? it.price;
    return value != null ? formatBRL(value) : '-';
  }
}

class _BestBadge extends StatelessWidget {
  const _BestBadge();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [AppColors.primaryDark, AppColors.primary],
          ),
          borderRadius: BorderRadius.circular(AppRadii.pill),
          boxShadow: appCardShadow(elevation: 0.4),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.emoji_events_rounded, size: 14, color: Colors.white),
            SizedBox(width: 4),
            Text(
              'MAIS BARATO',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.4,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionBtn extends StatelessWidget {
  const _ActionBtn({
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadii.sm),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Column(
            children: [
              Icon(icon, size: 24, color: AppColors.primary),
              const SizedBox(height: 4),
              Text(
                label,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.inkSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
