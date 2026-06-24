import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/providers.dart';
import 'policy_screen.dart';

/// Opt-in sheet for saving lists on the server (the LGPD consent toggle).
///
/// Enabling records consent + a server-side device record; disabling erases
/// everything stored for the device. The privacy policy is one tap away.
///
/// While consent/erase is in flight, [PopScope] blocks route pop (swipe/back)
/// so partial server/local state is less likely (#346).
class CloudSyncSheet extends ConsumerStatefulWidget {
  const CloudSyncSheet({super.key, this.onBusyChanged});

  /// Notifies the modal host when consent/erase is in progress (#346).
  final ValueChanged<bool>? onBusyChanged;

  static Future<void> show(BuildContext context) {
    return showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      // Barrier dismiss remains possible on some platforms; PopScope inside
      // blocks system/back and most modal pops while busy.
      isDismissible: true,
      enableDrag: true,
      builder: (ctx) => const _CloudSyncSheetRoute(),
    );
  }

  @override
  ConsumerState<CloudSyncSheet> createState() => _CloudSyncSheetState();
}

/// Owns busy state + [PopScope] for the modal route (#346).
class _CloudSyncSheetRoute extends StatefulWidget {
  const _CloudSyncSheetRoute();

  @override
  State<_CloudSyncSheetRoute> createState() => _CloudSyncSheetRouteState();
}

class _CloudSyncSheetRouteState extends State<_CloudSyncSheetRoute> {
  bool _busy = false;

  void _setBusy(bool value) {
    if (!mounted || _busy == value) return;
    setState(() => _busy = value);
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !_busy,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop && _busy && context.mounted) {
          ScaffoldMessenger.maybeOf(context)?.showSnackBar(
            const SnackBar(
              content: Text(
                'Aguarde o consentimento terminar antes de fechar.',
              ),
            ),
          );
        }
      },
      child: CloudSyncSheet(onBusyChanged: _setBusy),
    );
  }
}

class _CloudSyncSheetState extends ConsumerState<CloudSyncSheet> {
  bool _busy = false;

  Future<void> _toggle(bool value) async {
    setState(() => _busy = true);
    widget.onBusyChanged?.call(true);
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
      if (mounted) {
        setState(() => _busy = false);
        widget.onBusyChanged?.call(false);
      }
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
              subtitle: _busy
                  ? const Text(
                      'Processando consentimento… não feche esta tela.',
                    )
                  : null,
              value: enabled,
              onChanged: _busy ? null : _toggle,
            ),
            TextButton.icon(
              onPressed: _busy
                  ? null
                  : () {
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
