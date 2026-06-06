import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/providers.dart';

/// "Minhas lojas": view and remove the stores the user favourited or hid.
/// Needed because a hidden store no longer appears in results, so this is the
/// only place to un-hide it.
class StorePrefsSheet extends ConsumerWidget {
  const StorePrefsSheet({super.key});

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => const StorePrefsSheet(),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final favorites =
        ref.watch(favoriteStoresProvider).asData?.value ?? const {};
    final avoided = ref.watch(avoidedStoresProvider).asData?.value ?? const {};
    final text = Theme.of(context).textTheme;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Minhas lojas', style: text.titleLarge),
              const SizedBox(height: 4),
              Text(
                'Favoritas aparecem no topo dos resultados. Ocultas não aparecem.',
                style: text.bodyMedium?.copyWith(color: Colors.black54),
              ),
              const SizedBox(height: 16),
              _Group(
                icon: Icons.star,
                iconColor: Colors.amber,
                title: 'Favoritas',
                stores: favorites,
                emptyText: 'Nenhuma loja favorita ainda.',
                onRemove: (cnpj) =>
                    ref.read(favoriteStoresProvider.notifier).remove(cnpj),
              ),
              const SizedBox(height: 16),
              _Group(
                icon: Icons.visibility_off,
                iconColor: Colors.redAccent,
                title: 'Ocultas',
                stores: avoided,
                emptyText: 'Nenhuma loja oculta.',
                onRemove: (cnpj) =>
                    ref.read(avoidedStoresProvider.notifier).remove(cnpj),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Group extends StatelessWidget {
  const _Group({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.stores,
    required this.emptyText,
    required this.onRemove,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final Map<String, String> stores;
  final String emptyText;
  final void Function(String cnpj) onRemove;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: iconColor, size: 20),
            const SizedBox(width: 6),
            Text('$title (${stores.length})', style: text.titleMedium),
          ],
        ),
        const SizedBox(height: 4),
        if (stores.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(emptyText,
                style: text.bodyMedium?.copyWith(color: Colors.black54)),
          )
        else
          for (final entry in stores.entries)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(entry.value, style: const TextStyle(fontSize: 16)),
              trailing: IconButton(
                icon: const Icon(Icons.close),
                tooltip: 'Remover',
                onPressed: () => onRemove(entry.key),
              ),
            ),
      ],
    );
  }
}
