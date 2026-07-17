import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/config.dart';
import '../../core/theme.dart';

/// Detects iPhone/iPad/iPod in the browser user-agent (web only).
bool isIosWebUserAgent(String userAgent) {
  final ua = userAgent.toLowerCase();
  return ua.contains('iphone') ||
      ua.contains('ipad') ||
      ua.contains('ipod');
}

/// Web-only, dismissible install / home-screen banner — de-emphasized chrome.
class ApkBanner extends StatefulWidget {
  const ApkBanner({super.key, this.userAgentOverride, this.compact = false});

  final String? userAgentOverride;
  final bool compact;

  @override
  State<ApkBanner> createState() => _ApkBannerState();
}

class _ApkBannerState extends State<ApkBanner> {
  bool _dismissed = false;

  String get _ua =>
      widget.userAgentOverride ?? AppConfig.webUserAgent ?? '';

  @override
  Widget build(BuildContext context) {
    if (!kIsWeb || _dismissed) return const SizedBox.shrink();
    final ios = isIosWebUserAgent(_ua);
    final compact = widget.compact;
    return Container(
      margin: EdgeInsets.only(bottom: compact ? 6 : 10),
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 8 : 10,
        vertical: compact ? 4 : 8,
      ),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(compact ? 8 : 10),
        border: Border.all(color: AppColors.outline.withValues(alpha: 0.7)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Icon(
            ios ? Icons.ios_share_rounded : Icons.smartphone_rounded,
            size: compact ? 16 : 18,
            color: AppColors.inkMuted,
          ),
          SizedBox(width: compact ? 6 : 8),
          Expanded(
            child: Text(
              ios
                  ? (compact
                      ? 'iPhone: Compartilhar → Tela de Início'
                      : 'No iPhone/iPad: Compartilhar → Adicionar à Tela de Início')
                  : (compact
                      ? 'App Android disponível'
                      : 'Prefere o app? Baixe a versão Android.'),
              style: TextStyle(
                fontSize: compact ? 12 : 13,
                color: AppColors.inkMuted,
                fontWeight: FontWeight.w500,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (!ios)
            TextButton(
              onPressed: () => launchUrl(
                Uri.parse(AppConfig.androidApkUrl),
                mode: LaunchMode.externalApplication,
              ),
              style: TextButton.styleFrom(
                visualDensity: VisualDensity.compact,
                padding: const EdgeInsets.symmetric(horizontal: 8),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                foregroundColor: AppColors.primary,
                textStyle: TextStyle(
                  fontSize: compact ? 12 : 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
              child: const Text('Baixar'),
            ),
          IconButton(
            icon: Icon(Icons.close_rounded, size: compact ? 16 : 18),
            tooltip: 'Fechar',
            visualDensity: VisualDensity.compact,
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            padding: EdgeInsets.zero,
            color: AppColors.inkMuted,
            onPressed: () => setState(() => _dismissed = true),
          ),
        ],
      ),
    );
  }
}
