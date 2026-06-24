import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../data/providers.dart';
import '../settings/settings_sheet.dart';

/// Discloses Maceió/default search origin when GPS is unavailable or out of state (#304).
class ApproximateOriginBanner extends ConsumerWidget {
  const ApproximateOriginBanner({super.key, this.compact = false});

  /// When true, only show if [lastSearchOriginProvider] is approximate (post-search).
  /// When false, also probe is optional — we only show after a search set the flag
  /// so we do not spam permission dialogs on home load.
  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final origin = ref.watch(lastSearchOriginProvider);
    if (origin == null || !origin.approximate) {
      return const SizedBox.shrink();
    }

    return Card(
      margin: compact
          ? const EdgeInsets.fromLTRB(12, 8, 12, 4)
          : const EdgeInsets.only(bottom: 12),
      color: Colors.blue.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.location_off_outlined,
                color: Colors.blue.shade800, size: 28),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Buscando a partir de Maceió (referência)',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: Colors.blue.shade900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Não usamos sua localização real (permissão negada, GPS desligado, '
                    'fora de Alagoas ou indisponível). Preços e distâncias são relativos '
                    'ao centro de Maceió — ative a localização para resultados perto de você.',
                    style: TextStyle(fontSize: 13, color: Colors.blue.shade900),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      TextButton.icon(
                        onPressed: () async {
                          await Geolocator.openAppSettings();
                        },
                        icon: const Icon(Icons.settings, size: 18),
                        label: const Text('Abrir ajustes do aparelho'),
                      ),
                      TextButton.icon(
                        onPressed: () async {
                          await Geolocator.openLocationSettings();
                        },
                        icon: const Icon(Icons.gps_fixed, size: 18),
                        label: const Text('Ajustes de localização'),
                      ),
                      TextButton.icon(
                        onPressed: () => SettingsSheet.show(context),
                        icon: const Icon(Icons.tune, size: 18),
                        label: const Text('Aumentar raio na busca'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
