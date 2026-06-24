import 'package:compre_barato_alagoas/features/search/voice_input.dart';
import 'package:flutter_test/flutter_test.dart';
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
}
