import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/providers.dart';
import '../privacy/policy_screen.dart';
import '../stores/store_prefs_sheet.dart';

/// "Configurações": privacy/usage controls and store-preference management.
///
/// Hosts the LGPD opt-out for anonymous usage measurement (Art. 18 §2 — it
/// defaults ON because the legal basis is legítimo interesse, not consent),
/// the "Minhas lojas" management entry, and the policy link.
class SettingsSheet extends ConsumerWidget {
  const SettingsSheet({super.key});

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => const SettingsSheet(),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usageOn = ref.watch(usageStatsProvider).asData?.value ?? true;
    final text = Theme.of(context).textTheme;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Configurações', style: text.titleLarge),
            const SizedBox(height: 8),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.storefront),
              title: const Text('Minhas lojas', style: TextStyle(fontSize: 18)),
              subtitle: const Text('Lojas favoritas e ocultas'),
              onTap: () {
                Navigator.of(context).pop();
                StorePrefsSheet.show(context);
              },
            ),
            const Divider(),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Estatísticas anônimas de uso',
                  style: TextStyle(fontSize: 18)),
              subtitle: const Text(
                  'Ajuda a melhorar o app. Contagem anônima e agregada, sem '
                  'identificar você.'),
              value: usageOn,
              onChanged: (v) => ref.read(usageStatsProvider.notifier).set(v),
            ),
            TextButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const PolicyScreen()),
                );
              },
              icon: const Icon(Icons.privacy_tip_outlined),
              label: const Text('Política de Privacidade e Termos'),
            ),
          ],
        ),
      ),
    );
  }
}
