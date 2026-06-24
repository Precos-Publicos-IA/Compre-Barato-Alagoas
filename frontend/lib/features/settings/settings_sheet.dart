import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config.dart';
import '../../data/providers.dart';
import '../privacy/cloud_sync_sheet.dart';
import '../privacy/policy_screen.dart';
import '../stores/store_prefs_sheet.dart';

/// "Configurações": the single place for every user-adjustable setting —
/// search parameters (radius / recency), store preferences, the cloud-sync
/// (LGPD consent) toggle, the anonymous-usage opt-out and the policy link.
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
    final cloudOn = ref.watch(cloudSyncProvider).asData?.value ?? false;
    final params = ref.watch(searchPrefsProvider).asData?.value;
    final radius = params?.radiusKm ?? 8;
    final days = params?.days ?? 7;
    final text = Theme.of(context).textTheme;
    return SafeArea(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Configurações', style: text.titleLarge),
              const SizedBox(height: 8),

              // --- Search parameters (used on the next search) ---
              const Text('Parâmetros de busca',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              _SettingStepper(
                label: 'Distância máxima',
                valueLabel: '$radius km',
                onDec: () =>
                    ref.read(searchPrefsProvider.notifier).setRadius(radius - 1),
                onInc: () =>
                    ref.read(searchPrefsProvider.notifier).setRadius(radius + 1),
              ),
              _SettingStepper(
                label: 'Preços dos últimos',
                valueLabel: '$days dias',
                onDec: () =>
                    ref.read(searchPrefsProvider.notifier).setDays(days - 1),
                onInc: () =>
                    ref.read(searchPrefsProvider.notifier).setDays(days + 1),
              ),
              const Text(
                'Lojas mais distantes e preços mais antigos aparecem se você aumentar. Vale na próxima busca.',
                style: TextStyle(fontSize: 12, color: Colors.black54),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () =>
                      ref.read(searchPrefsProvider.notifier).reset(),
                  child: const Text('Restaurar padrões (8 km / 7 dias)',
                      style: TextStyle(fontSize: 12)),
                ),
              ),
              const Divider(),

              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.storefront),
                title:
                    const Text('Minhas lojas', style: TextStyle(fontSize: 18)),
                subtitle: const Text('Lojas favoritas e ocultas'),
                onTap: () {
                  Navigator.of(context).pop();
                  StorePrefsSheet.show(context);
                },
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(cloudOn ? Icons.cloud_done : Icons.cloud_outlined),
                title: const Text('Salvar listas na nuvem',
                    style: TextStyle(fontSize: 18)),
                subtitle: Text(cloudOn
                    ? 'Ativado — suas listas ficam guardadas neste aparelho e no servidor'
                    : 'Desativado — suas listas ficam só neste aparelho'),
                onTap: () {
                  Navigator.of(context).pop();
                  CloudSyncSheet.show(context);
                },
              ),
              const Divider(),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text(
                    'Estatísticas anônimas de uso (ajuda a melhorar o app para todo mundo)',
                    style: TextStyle(fontSize: 18)),
                subtitle: const Text(
                    'Contagem anônima e agregada (HyperLogLog). Não vemos o que você busca, não vendemos nada, não identificamos você. Desligue quando quiser. Usamos só para saber se o app está ajudando gente de verdade e para manter o servidor.'),
                value: usageOn,
                onChanged: (v) async {
                  try {
                    await ref.read(usageStatsProvider.notifier).set(v);
                  } on PrefsWriteException {
                    if (!context.mounted) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'Não foi possível salvar a preferência neste aparelho. Tente de novo.',
                        ),
                      ),
                    );
                  }
                },
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
              const SizedBox(height: 12),
              SelectableText(
                AppConfig.supportVersionLine,
                style: const TextStyle(fontSize: 12, color: Colors.black54),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A compact -/+ stepper row used for the numeric search parameters.
class _SettingStepper extends StatelessWidget {
  const _SettingStepper({
    required this.label,
    required this.valueLabel,
    required this.onDec,
    required this.onInc,
  });

  final String label;
  final String valueLabel;
  final VoidCallback onDec;
  final VoidCallback onInc;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 16))),
          IconButton(
            onPressed: onDec,
            icon: const Icon(Icons.remove_circle_outline),
            tooltip: 'Diminuir',
          ),
          SizedBox(
            width: 64,
            child: Text(valueLabel,
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w600)),
          ),
          IconButton(
            onPressed: onInc,
            icon: const Icon(Icons.add_circle_outline),
            tooltip: 'Aumentar',
          ),
        ],
      ),
    );
  }
}
