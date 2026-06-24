import 'package:compre_barato_alagoas/features/search/voice_input.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart';

LocaleName _loc(String id, [String name = '']) =>
    LocaleName(id, name.isEmpty ? id : name);

void main() {
  group('resolveSpeechLocaleId', () {
    test('prefers pt_BR when present', () {
      expect(
        resolveSpeechLocaleId([
          _loc('en_US'),
          _loc('pt_BR'),
          _loc('pt_PT'),
        ]),
        'pt_BR',
      );
    });

    test('accepts hyphenated pt-BR from iOS-style ids', () {
      expect(
        resolveSpeechLocaleId([_loc('pt-BR'), _loc('en_US')]),
        'pt-BR',
      );
    });

    test('falls back to pt_PT when pt_BR missing (common iPhone gap)', () {
      expect(
        resolveSpeechLocaleId([_loc('en_US'), _loc('pt_PT')]),
        'pt_PT',
      );
    });

    test('falls back to any pt_* when only generic Portuguese exists', () {
      expect(
        resolveSpeechLocaleId([_loc('de_DE'), _loc('pt_AO')]),
        'pt_AO',
      );
    });

    test('uses first device locale when no Portuguese at all', () {
      expect(
        resolveSpeechLocaleId([_loc('en_US'), _loc('es_ES')]),
        'en_US',
      );
    });

    test('returns preferred default when locale list is empty', () {
      expect(resolveSpeechLocaleId(const []), 'pt_BR');
    });
  });

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
