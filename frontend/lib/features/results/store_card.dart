import 'package:flutter/material.dart';

import '../../core/format.dart';
import '../../data/models.dart';
import 'store_actions.dart';

/// One store in the vertical results list. Collapsed it shows the essentials
/// (name, distance, total, and how much more it costs than the cheapest).
/// Tapping expands the item-by-item breakdown and the action buttons.
/// The cheapest store is highlighted and starts expanded.
class StoreCard extends StatefulWidget {
  const StoreCard({
    super.key,
    required this.store,
    required this.isBest,
    required this.deltaFromBest,
  });

  final StoreResult store;
  final bool isBest;

  /// How much more this store costs than the cheapest (0 for the cheapest).
  final double deltaFromBest;

  @override
  State<StoreCard> createState() => _StoreCardState();
}

class _StoreCardState extends State<StoreCard> {
  late bool _expanded = widget.isBest;

  String _priceDetail(ItemOffer it) {
    if (!it.quantityParsed || it.unitPrice == null || it.baseUnit == null) {
      return '';
    }
    if (it.baseUnit == 'un') {
      return (it.quantity ?? 1) > 1 ? '${formatBRL(it.unitPrice!)} cada' : '';
    }
    return formatUnitPrice(it.unitPrice!, it.baseUnit!);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final store = widget.store;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      color: widget.isBest ? scheme.primaryContainer : null,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: widget.isBest
            ? BorderSide(color: scheme.primary, width: 2)
            : BorderSide.none,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // --- Tappable header (always visible) ---
          InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 12, 14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (widget.isBest) const _BestBadge(),
                        Text(store.name,
                            style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 2),
                        Text(
                          [
                            if (store.distanceKm != null)
                              formatDistance(store.distanceKm),
                            '${store.itemsFound} de ${store.itemsTotal} itens',
                          ].join(' · '),
                          style: const TextStyle(
                              fontSize: 13, color: Colors.black54),
                        ),
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
                          fontSize: 26,
                          fontWeight: FontWeight.w800,
                          color: widget.isBest ? scheme.primary : null,
                        ),
                      ),
                      if (widget.deltaFromBest > 0)
                        Text(
                          '+${formatBRL(widget.deltaFromBest)}',
                          style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: scheme.error),
                        ),
                      Icon(
                        _expanded ? Icons.expand_less : Icons.expand_more,
                        color: Colors.black45,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          // --- Expanded detail ---
          if (_expanded) ...[
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (store.address != null) ...[
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        const Icon(Icons.place,
                            size: 16, color: Colors.black54),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(store.address!,
                              style: const TextStyle(
                                  fontSize: 14, color: Colors.black54)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                  ],
                  for (final it in store.items) _itemRow(it),
                  if (store.missing.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    const Text('Não encontrado nesta loja:',
                        style: TextStyle(
                            fontSize: 14, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        for (final m in store.missing)
                          Chip(
                            label:
                                Text(m, style: const TextStyle(fontSize: 13)),
                            backgroundColor: scheme.errorContainer,
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
                          icon: Icons.map,
                          label: 'Mapa',
                          onTap: () => StoreActions.openMaps(store)),
                      _ActionBtn(
                          icon: Icons.local_taxi,
                          label: 'Uber',
                          onTap: () => StoreActions.openUber(store)),
                      _ActionBtn(
                          icon: Icons.directions_car,
                          label: '99',
                          onTap: () => StoreActions.open99(store)),
                      _ActionBtn(
                          icon: Icons.copy,
                          label: 'Endereço',
                          onTap: () =>
                              StoreActions.copyAddress(context, store)),
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

  Widget _itemRow(ItemOffer it) {
    final detail = _priceDetail(it);
    final date = formatDate(it.saleDate);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(it.description ?? it.query,
                    style: const TextStyle(fontSize: 16)),
                if (detail.isNotEmpty)
                  Text(detail,
                      style: const TextStyle(
                          fontSize: 13, color: Colors.black54)),
                if (date.isNotEmpty)
                  Row(
                    children: [
                      const Icon(Icons.schedule,
                          size: 12, color: Colors.black45),
                      const SizedBox(width: 3),
                      Text('preço de $date',
                          style: const TextStyle(
                              fontSize: 12, color: Colors.black45)),
                    ],
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            it.price != null ? formatBRL(it.price!) : '-',
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _BestBadge extends StatelessWidget {
  const _BestBadge();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: scheme.primary,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.emoji_events, size: 16, color: scheme.onPrimary),
            const SizedBox(width: 4),
            Text('MAIS BARATO',
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: scheme.onPrimary)),
          ],
        ),
      ),
    );
  }
}

class _ActionBtn extends StatelessWidget {
  const _ActionBtn(
      {required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Column(
            children: [
              Icon(icon, size: 26, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 4),
              Text(label, style: const TextStyle(fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}
