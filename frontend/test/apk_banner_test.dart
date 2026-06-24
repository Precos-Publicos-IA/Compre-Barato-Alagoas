import 'package:compre_barato_alagoas/features/search/apk_banner.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('isIosWebUserAgent', () {
    test('detects iPhone Safari', () {
      expect(
        isIosWebUserAgent(
          'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
          'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 '
          'Mobile/15E148 Safari/604.1',
        ),
        isTrue,
      );
    });

    test('detects iPad', () {
      expect(
        isIosWebUserAgent(
          'Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
        ),
        isTrue,
      );
    });

    test('does not treat Android Chrome as iOS', () {
      expect(
        isIosWebUserAgent(
          'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
          'Chrome/120.0.0.0 Mobile Safari/537.36',
        ),
        isFalse,
      );
    });

    test('does not treat desktop Chrome as iOS', () {
      expect(
        isIosWebUserAgent(
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        ),
        isFalse,
      );
    });
  });
}
