import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/providers.dart';
import 'policy_screen.dart';

/// Opt-in sheet for saving lists on the server (the LGPD consent toggle).
///
/// Enabling records consent + a server-side device record; disabling erases
/// everything stored for the device. The privacy policy is one tap away.
class CloudSyncSheet extends ConsumerStatefulWidget {
  const CloudSyncSheet({super.key});

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => const CloudSyncSheet(),
    );
  }

  @override
  ConsumerState<CloudSyncSheet> createState() => _CloudSyncSheetState();
}

class _CloudSyncSheetState extends ConsumerState<CloudSyncSheet> {
  bool _busy = false;

  Future<void> _toggle(bool value) async {
    setState(() => _busy = true);
    final notifier = ref.read(cloudSyncProvider.notifier);
    try {
      if (value) {
        await notifier.enable();
      } else {
        await notifier.disable();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString())),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final enabled = ref.watch(cloudSyncProvider).asData?.value ?? false;
    final text = Theme.of(context).textTheme;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.cloud_outlined),
                const SizedBox(width: 8),
                Expanded(
                  child: Text('Salvar minhas listas na nuvem',
                      style: text.titleLarge),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Sem cadastro e sem senha. Usamos um identificador anônimo do '
              'aparelho para guardar suas listas no servidor. Se trocar ou '
              'perder o aparelho, esses dados se perdem.',
              style: text.bodyMedium?.copyWith(height: 1.4),
            ),
            const SizedBox(height: 8),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Ativar', style: TextStyle(fontSize: 18)),
              subtitle: _busy ? const Text('Salvando…') : null,
              value: enabled,
              onChanged: _busy ? null : _toggle,
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
