import 'package:compre_barato_alagoas/data/api_client.dart';
import 'package:compre_barato_alagoas/data/device_identity.dart';
import 'package:compre_barato_alagoas/data/providers.dart';
import 'package:compre_barato_alagoas/features/privacy/cloud_sync_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _FakeDeviceIdentity extends DeviceIdentity {
  @override
  Future<String> getOrCreateToken() async => 'a' * 64;
}

/// Records consent/erasure calls instead of hitting the network.
class _RecordingApiClient extends ApiClient {
  _RecordingApiClient() : super(baseUrl: 'http://test.local');
  String? consentedToken;
  String? deletedToken;

  @override
  Future<void> registerConsent(String deviceToken, String policyVersion) async {
    consentedToken = deviceToken;
  }

  @override
  Future<void> deleteDevice(String deviceToken) async {
    deletedToken = deviceToken;
  }
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('toggling cloud sync registers then erases consent',
      (tester) async {
    final api = _RecordingApiClient();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(api),
          deviceIdentityProvider.overrideWithValue(_FakeDeviceIdentity()),
        ],
        child: const MaterialApp(home: Scaffold(body: CloudSyncSheet())),
      ),
    );
    await tester.pumpAndSettle();

    // Opt in → consent recorded for the device token.
    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();
    expect(api.consentedToken, 'a' * 64);

    // Opt out → LGPD erasure for the same token.
    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();
    expect(api.deletedToken, 'a' * 64);
  });
}
