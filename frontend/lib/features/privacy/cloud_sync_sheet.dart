import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/api_client.dart';
import '../../data/providers.dart';
import 'policy_screen.dart';

/// User-facing consent/erase errors (no Exception.toString noise) (#400).
String cloudSyncErrorMessage(Object error) {
  if (error is CloudSyncLocalMirrorException) {
    return 'Preferências do aparelho não puderam ser salvas. '
        'Tente de novo; se o problema continuar, reinicie o app.';
  }
  if (error is ApiException) {
    final id = error.requestId?.trim();
    if (id != null && id.isNotEmpty) {
      return '${error.message}\n(ref: $id)';
    }
    return error.message;
  }
  final s = error.toString();
  if (s.contains('TimeoutException') || s.toLowerCase().contains('timeout')) {
    return 'A operação demorou demais. Verifique a conexão e tente de novo.';
  }
  if (s.contains('ClientException') || s.contains('SocketException')) {
    return 'Sem conexão com o servidor. Verifique a rede e tente de novo.';
  }
  return 'Não foi possível atualizar a preferência de nuvem. Tente de novo.';
}

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
  String? _statusMessage;
  bool _statusIsError = false;

  Future<void> _toggle(bool value) async {
    setState(() {
      _busy = true;
      _statusMessage = null;
      _statusIsError = false;
    });
    final notifier = ref.read(cloudSyncProvider.notifier);
    try {
      if (value) {
        await notifier.enable();
      } else {
        await notifier.disable();
      }
      if (mounted) {
        setState(() {
          _statusMessage = value
              ? 'Listas na nuvem ativadas neste aparelho.'
              : 'Dados do aparelho apagados no servidor.';
          _statusIsError = false;
        });
      }
    } catch (e) {
      if (mounted) {
        final msg = cloudSyncErrorMessage(e);
        setState(() {
          _statusMessage = msg;
          _statusIsError = true;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg)),
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
            if (_statusMessage != null) ...[
              const SizedBox(height: 4),
              Semantics(
                liveRegion: true,
                child: Text(
                  _statusMessage!,
                  style: TextStyle(
                    fontSize: 14,
                    color: _statusIsError
                        ? Theme.of(context).colorScheme.error
                        : Colors.black87,
                  ),
                ),
              ),
            ],
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
