import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/config.dart';
import '../../core/web_display_mode_stub.dart'
    if (dart.library.html) '../../core/web_display_mode_web.dart' as display_mode;

/// Detects iPhone/iPad/iPod in the browser user-agent (web only).
///
/// Kept pure/testable so we do not show Android APK CTAs on iOS Safari, where
/// the only install path today is "Add to Home Screen" (no App Store build yet).
bool isIosWebUserAgent(String userAgent) {
  final ua = userAgent.toLowerCase();
  return ua.contains('iphone') ||
      ua.contains('ipad') ||
      ua.contains('ipod');
}

/// Web-only, dismissible install / home-screen banner.
///
/// - **Android / non-iOS browsers**: offer the APK download.
/// - **iPhone/iPad Safari**: explain how to add the web app to the Home Screen
///   (native iOS app is tracked separately; no misleading APK button).
/// - Hidden when already in `display-mode: standalone` / iOS A2HS (#391).
///
/// Renders nothing outside the web build.
class ApkBanner extends StatefulWidget {
  const ApkBanner({
    super.key,
    this.userAgentOverride,
    this.standaloneOverride,
  });

  /// Injected in tests; production reads [AppConfig.webUserAgent] / platform.
  final String? userAgentOverride;

  /// Injected in tests; production uses [display_mode.isStandaloneDisplayMode].
  final bool? standaloneOverride;

  @override
  State<ApkBanner> createState() => _ApkBannerState();
}

class _ApkBannerState extends State<ApkBanner> {
  bool _dismissed = false;

  String get _ua =>
      widget.userAgentOverride ?? AppConfig.webUserAgent ?? '';

  bool get _standalone =>
      widget.standaloneOverride ?? display_mode.isStandaloneDisplayMode();

  @override
  Widget build(BuildContext context) {
    if (!kIsWeb || _dismissed || _standalone) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    final ios = isIosWebUserAgent(_ua);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.secondaryContainer,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(ios ? Icons.ios_share : Icons.android, size: 28),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              ios
                  ? 'No iPhone/iPad: toque em Compartilhar e depois em '
                      '"Adicionar à Tela de Início" para usar como app.'
                  : 'Use no celular: baixe o app Android.',
              style: const TextStyle(fontSize: 15),
            ),
          ),
          if (!ios)
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
