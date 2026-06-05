import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/config.dart';

/// Web-only, dismissible banner inviting the user to install the Android app.
/// Renders nothing outside the web build.
class ApkBanner extends StatefulWidget {
  const ApkBanner({super.key});

  @override
  State<ApkBanner> createState() => _ApkBannerState();
}

class _ApkBannerState extends State<ApkBanner> {
  bool _dismissed = false;

  @override
  Widget build(BuildContext context) {
    if (!kIsWeb || _dismissed) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.secondaryContainer,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          const Icon(Icons.android, size: 28),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              'Use no celular: baixe o app Android.',
              style: TextStyle(fontSize: 15),
            ),
          ),
          TextButton(
            onPressed: () => launchUrl(
              Uri.parse(AppConfig.androidApkUrl),
              mode: LaunchMode.externalApplication,
            ),
            child: const Text('Baixar APK'),
          ),
          IconButton(
            icon: const Icon(Icons.close),
            tooltip: 'Fechar',
            onPressed: () => setState(() => _dismissed = true),
          ),
        ],
      ),
    );
  }
}
