import 'package:flutter/foundation.dart'
    show TargetPlatform, defaultTargetPlatform, kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../data/models.dart';

/// Builds ordered external map/directions URL candidates for a store.
///
/// iPhone/iPad users get Apple Maps first (default map app); other platforms
/// prefer Google Maps. Android also gets `geo:` early so the system chooser can
/// open any maps app. Waze app + HTTPS are included for BR driving (#338).
/// Exposed for unit tests without invoking [url_launcher].
List<String> buildMapUrls(StoreResult s, {TargetPlatform? platform, bool? isWeb}) {
  final web = isWeb ?? kIsWeb;
  final plat = platform ?? defaultTargetPlatform;
  final preferApple = !web && plat == TargetPlatform.iOS;
  final preferAndroid = !web && plat == TargetPlatform.android;
  final urls = <String>[];

  if (s.latitude != null && s.longitude != null) {
    final lat = s.latitude!;
    final lon = s.longitude!;
    final q = Uri.encodeComponent(s.name);
    final geo = 'geo:$lat,$lon?q=$lat,$lon($q)';
    final wazeApp = 'waze://?ll=$lat,$lon&navigate=yes';
    final wazeWeb =
        'https://waze.com/ul?ll=${Uri.encodeComponent('$lat,$lon')}&navigate=yes';
    final apple = 'https://maps.apple.com/?ll=$lat,$lon&q=$q';
    final google =
        'https://www.google.com/maps/search/?api=1&query=$lat,$lon';
    if (preferAndroid) {
      // geo: first — lets Android offer installed map apps (incl. Waze/Google).
      urls.add(geo);
      urls.add(wazeApp);
      urls.add(google);
      urls.add(wazeWeb);
      urls.add(apple);
    } else if (preferApple) {
      urls.add(apple);
      urls.add(wazeApp);
      urls.add(google);
      urls.add(wazeWeb);
    } else {
      urls.add(google);
      urls.add(wazeWeb);
      urls.add(apple);
    }
  }
  if (s.address != null && s.address!.trim().isNotEmpty) {
    final addr = Uri.encodeComponent(s.address!);
    final apple = 'https://maps.apple.com/?q=$addr';
    final google =
        'https://www.google.com/maps/search/?api=1&query=$addr';
    if (preferApple) {
      urls.add(apple);
      urls.add(google);
    } else {
      urls.add(google);
      urls.add(apple);
    }
  }
  return urls;
}

/// Directions candidates (used when 99 has no stable deep link).
List<String> buildDirectionsUrls(StoreResult s,
    {TargetPlatform? platform, bool? isWeb}) {
  if (s.latitude == null || s.longitude == null) return const [];
  final web = isWeb ?? kIsWeb;
  final plat = platform ?? defaultTargetPlatform;
  final preferApple = !web && plat == TargetPlatform.iOS;
  final preferAndroid = !web && plat == TargetPlatform.android;
  final lat = s.latitude!;
  final lon = s.longitude!;
  final geo = 'geo:$lat,$lon?q=$lat,$lon';
  final wazeApp = 'waze://?ll=$lat,$lon&navigate=yes';
  final wazeWeb =
      'https://waze.com/ul?ll=${Uri.encodeComponent('$lat,$lon')}&navigate=yes';
  final apple = 'https://maps.apple.com/?daddr=$lat,$lon';
  final google =
      'https://www.google.com/maps/dir/?api=1&destination=$lat,$lon';
  if (preferAndroid) {
    return [geo, wazeApp, google, wazeWeb, apple];
  }
  if (preferApple) {
    return [apple, wazeApp, google, wazeWeb];
  }
  return [google, wazeWeb, apple];
}

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
    await _launchFirst(buildMapUrls(s));
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
    // maps directions (Apple on iOS, Google elsewhere) so the user still gets
    // navigation.
    await _launchFirst([
      'taxis99://call?dropoff_latitude=${s.latitude}&dropoff_longitude=${s.longitude}',
      '99app://',
      ...buildDirectionsUrls(s),
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
