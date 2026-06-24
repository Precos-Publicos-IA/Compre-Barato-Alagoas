import 'package:compre_barato_alagoas/data/models.dart';
import 'package:compre_barato_alagoas/features/results/store_actions.dart';
import 'package:flutter/foundation.dart' show TargetPlatform;
import 'package:flutter_test/flutter_test.dart';

StoreResult _store({
  double? lat = -9.66,
  double? lon = -35.73,
  String? address = 'Rua X, Maceió',
}) =>
    StoreResult(
      cnpj: '1',
      name: 'Mercado Teste',
      itemsFound: 1,
      itemsTotal: 1,
      total: 10,
      items: const [],
      missing: const [],
      latitude: lat,
      longitude: lon,
      address: address,
    );

void main() {
  group('buildMapUrls', () {
    test('iOS prioritizes Apple Maps over Google', () {
      final urls = buildMapUrls(
        _store(),
        platform: TargetPlatform.iOS,
        isWeb: false,
      );
      expect(urls.first, startsWith('https://maps.apple.com/'));
      expect(urls.first, contains('ll=-9.66,-35.73'));
      expect(urls.any((u) => u.contains('google.com/maps')), isTrue);
      expect(urls.indexOf(urls.firstWhere((u) => u.contains('maps.apple.com'))),
          lessThan(urls.indexOf(
              urls.firstWhere((u) => u.contains('google.com/maps')))));
    });

    test('Android leads with geo: then Waze then Google', () {
      final urls = buildMapUrls(
        _store(),
        platform: TargetPlatform.android,
        isWeb: false,
      );
      expect(urls.first, startsWith('geo:'));
      expect(urls.any((u) => u.startsWith('waze://')), isTrue);
      expect(urls.any((u) => u.contains('waze.com/ul')), isTrue);
      expect(urls.any((u) => u.contains('google.com/maps')), isTrue);
      expect(urls.any((u) => u.contains('maps.apple.com')), isTrue);
    });

    test('iOS includes Waze candidates after Apple', () {
      final urls = buildMapUrls(
        _store(),
        platform: TargetPlatform.iOS,
        isWeb: false,
      );
      expect(urls.first, startsWith('https://maps.apple.com/'));
      expect(urls.any((u) => u.startsWith('waze://')), isTrue);
    });

    test('web prioritizes Google even on iOS UA simulation', () {
      final urls = buildMapUrls(
        _store(),
        platform: TargetPlatform.iOS,
        isWeb: true,
      );
      expect(urls.first, contains('google.com/maps'));
      expect(urls.any((u) => u.contains('waze.com/ul')), isTrue);
      expect(urls.any((u) => u.startsWith('geo:')), isFalse);
    });

    test('includes encoded address candidates when address present', () {
      final urls = buildMapUrls(
        _store(lat: null, lon: null, address: 'Av. Brasil, 100'),
        platform: TargetPlatform.iOS,
        isWeb: false,
      );
      expect(urls, isNotEmpty);
      expect(urls.first, startsWith('https://maps.apple.com/?q='));
      expect(urls.first, contains(Uri.encodeComponent('Av. Brasil, 100')));
    });
  });

  group('buildDirectionsUrls', () {
    test('iOS lists Apple directions before Google and includes Waze', () {
      final urls = buildDirectionsUrls(
        _store(),
        platform: TargetPlatform.iOS,
        isWeb: false,
      );
      expect(urls.first, startsWith('https://maps.apple.com/?daddr='));
      expect(urls.any((u) => u.contains('google.com/maps/dir')), isTrue);
      expect(urls.any((u) => u.startsWith('waze://')), isTrue);
    });

    test('Android directions include geo and Waze', () {
      final urls = buildDirectionsUrls(
        _store(),
        platform: TargetPlatform.android,
        isWeb: false,
      );
      expect(urls.first, startsWith('geo:'));
      expect(urls.any((u) => u.startsWith('waze://')), isTrue);
    });

    test('returns empty without coordinates', () {
      expect(
        buildDirectionsUrls(
          _store(lat: null, lon: null),
          platform: TargetPlatform.iOS,
          isWeb: false,
        ),
        isEmpty,
      );
    });
  });
}
