import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/models.dart';

/// Launches store-related external actions (maps, ride apps, clipboard).
/// Each ride/map action tries the native app first, then a web fallback.
class StoreActions {
  static Future<void> _launchFirst(List<String> urls) async {
    for (final u in urls) {
      try {
        if (await launchUrl(Uri.parse(u),
            mode: LaunchMode.externalApplication)) {
          return;
        }
      } catch (_) {
        // try the next candidate
      }
    }
  }

  static String _destLabel(StoreResult s) => s.name;

  static Future<void> openMaps(StoreResult s) async {
    final urls = <String>[];
    if (s.latitude != null && s.longitude != null) {
      urls.add(
        'https://www.google.com/maps/search/?api=1&query=${s.latitude},${s.longitude}',
      );
    }
    if (s.address != null) {
      urls.add(
        'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(s.address!)}',
      );
    }
    await _launchFirst(urls);
  }

  static Future<void> openUber(StoreResult s) async {
    if (s.latitude == null || s.longitude == null) return openMaps(s);
    final name = Uri.encodeComponent(_destLabel(s));
    await _launchFirst([
      'uber://?action=setPickup&pickup=my_location'
          '&dropoff[latitude]=${s.latitude}&dropoff[longitude]=${s.longitude}'
          '&dropoff[nickname]=$name',
      'https://m.uber.com/ul/?action=setPickup&pickup=my_location'
          '&dropoff[latitude]=${s.latitude}&dropoff[longitude]=${s.longitude}'
          '&dropoff[nickname]=$name',
    ]);
  }

  static Future<void> open99(StoreResult s) async {
    if (s.latitude == null || s.longitude == null) return openMaps(s);
    // 99 has no stable public deep-link spec; try the app, then fall back to
    // Google Maps directions which gets the user there regardless.
    await _launchFirst([
      'taxis99://call?dropoff_latitude=${s.latitude}&dropoff_longitude=${s.longitude}',
      '99app://',
      'https://www.google.com/maps/dir/?api=1&destination=${s.latitude},${s.longitude}',
    ]);
  }

  static Future<void> copyAddress(BuildContext context, StoreResult s) async {
    final text = s.address ?? s.name;
    await Clipboard.setData(ClipboardData(text: text));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Endereço copiado: $text')),
      );
    }
  }
}
