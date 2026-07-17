import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../data/providers.dart';
import '../privacy/cloud_sync_sheet.dart';
import '../privacy/policy_screen.dart';
import '../stores/store_prefs_sheet.dart';

/// "Configurações": search params, store prefs, cloud-sync, usage opt-out.
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
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Configurações', style: text.headlineSmall),
              const SizedBox(height: 4),
              Text(
                'Ajustes de busca e privacidade',
                style: text.bodyMedium?.copyWith(color: AppColors.inkMuted),
              ),
              const SizedBox(height: 16),

              Text(
                'Parâmetros de busca',
                style: text.titleSmall?.copyWith(color: AppColors.inkMuted),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppRadii.md),
                  border: Border.all(color: AppColors.outline),
                ),
                child: Column(
                  children: [
                    _SettingStepper(
                      label: 'Distância máxima',
                      valueLabel: '$radius km',
                      onDec: () => ref
                          .read(searchPrefsProvider.notifier)
                          .setRadius(radius - 1),
                      onInc: () => ref
                          .read(searchPrefsProvider.notifier)
                          .setRadius(radius + 1),
                    ),
                    Divider(height: 8, color: AppColors.outline.withValues(alpha: 0.7)),
                    _SettingStepper(
                      label: 'Preços dos últimos',
                      valueLabel: '$days dias',
                      onDec: () =>
                          ref.read(searchPrefsProvider.notifier).setDays(days - 1),
                      onInc: () =>
                          ref.read(searchPrefsProvider.notifier).setDays(days + 1),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Lojas mais distantes e preços mais antigos aparecem se você aumentar. Vale na próxima busca.',
                style: text.bodySmall,
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () =>
                      ref.read(searchPrefsProvider.notifier).reset(),
                  child: const Text(
                    'Restaurar padrões (8 km / 7 dias)',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              _SettingsTile(
                icon: Icons.storefront_outlined,
                title: 'Minhas lojas',
                subtitle: 'Lojas favoritas e ocultas',
                onTap: () {
                  Navigator.of(context).pop();
                  StorePrefsSheet.show(context);
                },
              ),
              _SettingsTile(
                icon: cloudOn ? Icons.cloud_done_rounded : Icons.cloud_outlined,
                title: 'Salvar listas na nuvem',
                subtitle: cloudOn
                    ? 'Ativado — listas neste aparelho e no servidor'
                    : 'Desativado — listas só neste aparelho',
                onTap: () {
                  Navigator.of(context).pop();
                  CloudSyncSheet.show(context);
                },
              ),
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppRadii.md),
                  border: Border.all(color: AppColors.outline),
                ),
                child: SwitchListTile(
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  title: const Text(
                    'Estatísticas anônimas de uso',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                  ),
                  subtitle: const Text(
                    'Contagem anônima e agregada. Não vemos o que você busca. Desligue quando quiser.',
                    style: TextStyle(fontSize: 13),
                  ),
                  value: usageOn,
                  activeThumbColor: AppColors.primary,
                  onChanged: (v) =>
                      ref.read(usageStatsProvider.notifier).set(v),
                ),
              ),
              const SizedBox(height: 8),
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
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(color: AppColors.outline),
      ),
      child: ListTile(
        onTap: onTap,
        leading: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: AppColors.primarySoft,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: AppColors.primary, size: 22),
        ),
        title: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 13)),
        trailing: const Icon(Icons.chevron_right_rounded, color: AppColors.inkMuted),
      ),
    );
  }
}

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
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
            ),
          ),
          IconButton(
            onPressed: onDec,
            icon: const Icon(Icons.remove_circle_outline_rounded),
            tooltip: 'Diminuir',
          ),
          SizedBox(
            width: 72,
            child: Text(
              valueLabel,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppColors.primary,
              ),
            ),
          ),
          IconButton(
            onPressed: onInc,
            icon: const Icon(Icons.add_circle_outline_rounded),
            tooltip: 'Aumentar',
          ),
        ],
      ),
    );
  }
}
