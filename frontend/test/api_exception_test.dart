import 'package:compre_barato_alagoas/data/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

void main() {
  group('ApiException', () {
    test('toString is message only without requestId', () {
      expect(ApiException('falhou').toString(), 'falhou');
    });

    test('toString appends ref when requestId set', () {
      expect(
        ApiException('falhou', requestId: 'abc123def456').toString(),
        'falhou (ref: abc123def456)',
      );
    });

    test('trims empty requestId', () {
      expect(ApiException('x', requestId: '  ').toString(), 'x');
    });
  });

  group('ApiClient.requestIdOf', () {
    test('reads x-request-id header', () {
      final resp = http.Response('{}', 500, headers: {'x-request-id': 'deadbeef01'});
      expect(ApiClient.requestIdOf(resp), 'deadbeef01');
    });

    test('returns null when missing', () {
      final resp = http.Response('{}', 500);
      expect(ApiClient.requestIdOf(resp), isNull);
    });
  });
}
