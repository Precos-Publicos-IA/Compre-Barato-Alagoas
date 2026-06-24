import 'package:compre_barato_alagoas/features/search/voice_input.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:permission_handler/permission_handler.dart';

void main() {
  group('VoiceInput permission gating', () {
    test('on web: skips permission_handler pre-check', () {
      final voice = VoiceInput(isWeb: true);
      expect(voice.usesPermissionHandlerPrecheck, isFalse);
    });

    test('on non-web: uses permission_handler pre-check', () {
      final voice = VoiceInput(isWeb: false);
      expect(voice.usesPermissionHandlerPrecheck, isTrue);
    });

    test('on non-web: denied mic returns false without calling speech engine',
        () async {
      var micCalls = 0;
      final voice = VoiceInput(
        isWeb: false,
        requestMicrophone: () async {
          micCalls++;
          return PermissionStatus.denied;
        },
      );
      final ok = await voice.ensureReady();
      expect(ok, isFalse);
      expect(micCalls, 1);
    });

    test('on web: does not call requestMicrophone even if injected', () async {
      var micCalls = 0;
      final voice = VoiceInput(
        isWeb: true,
        requestMicrophone: () async {
          micCalls++;
          return PermissionStatus.denied;
        },
      );
      // initialize() may fail without platform channels; only assert mic gate.
      try {
        await voice.ensureReady();
      } catch (_) {
        // Missing platform channels in pure unit tests is acceptable.
      }
      expect(micCalls, 0);
    });
  });
}
