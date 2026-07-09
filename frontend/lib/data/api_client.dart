import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import 'models.dart';

class ApiException implements Exception {
  final String message;

  /// Server `X-Request-ID` when present — helps support correlate logs/Sentry (#136).
  final String? requestId;

  ApiException(this.message, {this.requestId});

  @override
  String toString() {
    final id = requestId?.trim();
    if (id == null || id.isEmpty) return message;
    return '$message (ref: $id)';
  }
}

/// Thin HTTP client for the Compre Barato Alagoas backend.
class ApiClient {
  ApiClient({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = baseUrl ?? AppConfig.apiBaseUrl;

  final http.Client _client;
  final String _baseUrl;

  /// Per-request ceiling so a stalled network surfaces instead of hanging the UI.
  static const Duration _timeout = Duration(seconds: 12);
  /// Web SEFAZ multi-item baskets can take a minute+ cold.
  static const Duration _searchTimeout = Duration(seconds: 120);

  /// Runs [send] with a timeout and a single retry on transient transport
  /// failures (timeout / connection drop). HTTP error *statuses* return a
  /// normal Response and are handled by the caller — they are not retried.
  Future<http.Response> _retry(Future<http.Response> Function() send) async {
    for (var attempt = 0;; attempt++) {
      try {
        return await send().timeout(_timeout);
      } on TimeoutException {
        if (attempt >= 1) rethrow;
      } on http.ClientException {
        if (attempt >= 1) rethrow;
      }
      await Future<void>.delayed(const Duration(milliseconds: 400));
    }
  }

  Future<http.Response> _get(Uri uri, {Map<String, String>? headers}) =>
      _retry(() => _client.get(uri, headers: headers));

  Future<http.Response> _post(Uri uri,
          {Map<String, String>? headers, Object? body}) =>
      _retry(() => _client.post(uri, headers: headers, body: body));

  /// Reads `X-Request-ID` from a response (header names are case-insensitive in http).
  static String? requestIdOf(http.Response resp) {
    final raw = resp.headers['x-request-id'] ?? resp.headers['X-Request-ID'];
    if (raw == null) return null;
    final t = raw.trim();
    return t.isEmpty ? null : t;
  }

  Never _throwHttp(String message, http.Response resp) =>
      throw ApiException(message, requestId: requestIdOf(resp));

  Future<List<Suggestion>> fetchSuggestions() async {
    final uri = Uri.parse('$_baseUrl/api/v1/suggestions');
    final resp = await _get(uri);
    if (resp.statusCode != 200) {
      _throwHttp('Falha ao carregar sugestões (${resp.statusCode})', resp);
    }
    final body = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return (body['items'] as List<dynamic>)
        .map((e) => Suggestion.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Resolves a shared list UUID into its items. Returns null if the link has
  /// expired or doesn't exist (HTTP 404).
  Future<List<String>?> fetchList(String listId) async {
    final uri = Uri.parse('$_baseUrl/api/v1/lists/$listId');
    final resp = await _get(uri);
    if (resp.statusCode == 404) return null;
    if (resp.statusCode != 200) {
      _throwHttp('Não foi possível abrir a lista compartilhada.', resp);
    }
    final body = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return (body['items'] as List<dynamic>).map((e) => e as String).toList();
  }

  /// Header carrying the pseudo-anonymous device token (a bearer credential).
  static const String deviceTokenHeader = 'X-Device-Token';

  /// Header carrying the anonymous usage-measurement id (not a credential).
  static const String analyticsIdHeader = 'X-Analytics-Id';

  Future<SearchResponse> search(
    List<String> items, {
    double? latitude,
    double? longitude,
    int? radiusKm,
    int? days,
    String? deviceToken,
    String? analyticsId,
    List<String> excludedCnpjs = const [],
    List<String> favoriteCnpjs = const [],
  }) async {
    final uri = Uri.parse('$_baseUrl/api/v1/search');
    final payload = <String, dynamic>{
      'items': items,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (radiusKm != null) 'radius_km': radiusKm,
      if (days != null) 'days': days,
      if (excludedCnpjs.isNotEmpty) 'excluded_cnpjs': excludedCnpjs,
      if (favoriteCnpjs.isNotEmpty) 'favorite_cnpjs': favoriteCnpjs,
    };
    final resp = await _post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        // Sent only when the user opted into cloud sync, so consented devices
        // get this list saved to their server-side history.
        deviceTokenHeader: ?deviceToken,
        // Sent on every search unless usage stats are off (LGPD opt-out).
        analyticsIdHeader: ?analyticsId,
      },
      body: jsonEncode(payload),
    );
    if (resp.statusCode == 429) {
      _throwHttp('Você atingiu o limite de buscas de hoje.', resp);
    }
    if (resp.statusCode != 200) {
      _throwHttp('Não foi possível buscar os preços agora.', resp);
    }
    final body = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return SearchResponse.fromJson(body);
  }

  /// Progressive NDJSON search. Calls [onStatus] and [onPartial] as events arrive.
  /// Returns the final [SearchResponse] from the `done` event (or last partial).
  Future<SearchResponse> searchStream(
    List<String> items, {
    double? latitude,
    double? longitude,
    int? radiusKm,
    int? days,
    String? deviceToken,
    String? analyticsId,
    List<String> excludedCnpjs = const [],
    List<String> favoriteCnpjs = const [],
    void Function(String message)? onStatus,
    void Function(SearchResponse partial)? onPartial,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/v1/search/stream');
    final payload = <String, dynamic>{
      'items': items,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (radiusKm != null) 'radius_km': radiusKm,
      if (days != null) 'days': days,
      if (excludedCnpjs.isNotEmpty) 'excluded_cnpjs': excludedCnpjs,
      if (favoriteCnpjs.isNotEmpty) 'favorite_cnpjs': favoriteCnpjs,
    };
    final request = http.Request('POST', uri)
      ..headers.addAll({
        'Content-Type': 'application/json',
        'Accept': 'application/x-ndjson',
        if (deviceToken != null) deviceTokenHeader: deviceToken,
        if (analyticsId != null) analyticsIdHeader: analyticsId,
      })
      ..body = jsonEncode(payload);

    final streamed = await _client.send(request).timeout(_searchTimeout);
    if (streamed.statusCode == 429) {
      throw ApiException('Você atingiu o limite de buscas de hoje.');
    }
    if (streamed.statusCode != 200) {
      final body = await streamed.stream.bytesToString();
      throw ApiException(
        'Não foi possível buscar os preços agora. (${streamed.statusCode}) $body',
      );
    }

    SearchResponse? last;
    final buffer = StringBuffer();
    await for (final chunk in streamed.stream.transform(utf8.decoder)) {
      buffer.write(chunk);
      var data = buffer.toString();
      while (true) {
        final nl = data.indexOf('\n');
        if (nl < 0) break;
        final line = data.substring(0, nl).trim();
        data = data.substring(nl + 1);
        if (line.isEmpty) continue;
        late final Map<String, dynamic> ev;
        try {
          ev = jsonDecode(line) as Map<String, dynamic>;
        } catch (_) {
          continue;
        }
        final type = ev['type'] as String? ?? '';
        if (type == 'status') {
          final msg = ev['message'] as String?;
          if (msg != null && msg.isNotEmpty) onStatus?.call(msg);
        } else if (type == 'partial' || type == 'done') {
          final resp = ev['response'];
          if (resp is Map<String, dynamic>) {
            last = SearchResponse.fromJson(resp);
            if (type == 'partial') {
              onPartial?.call(last!);
              final sm = last!.metrics.statusMessage;
              if (sm != null && sm.isNotEmpty) onStatus?.call(sm);
            }
          }
        } else if (type == 'error') {
          throw ApiException(
            (ev['detail'] as String?) ??
                'Não foi possível buscar os preços agora.',
          );
        }
      }
      buffer
        ..clear()
        ..write(data);
    }
    if (last == null) {
      throw ApiException('Não foi possível buscar os preços agora.');
    }
    return last;
  }

  /// Sends user feedback on results (👍/👎 or "item errado"). Best-effort and
  /// anonymous by default; a device token is sent only if the caller passes one
  /// (consented devices). Never throws on the UI path — returns false on failure.
  Future<bool> submitFeedback({
    required String kind,
    bool? helpful,
    String? item,
    String? note,
    String? listId,
    String? deviceToken,
  }) async {
    try {
      final uri = Uri.parse('$_baseUrl/api/v1/feedback');
      final resp = await _client.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          deviceTokenHeader: ?deviceToken,
        },
        body: jsonEncode({
          'kind': kind,
          'helpful': ?helpful,
          'item': ?item,
          'note': ?note,
          'list_id': ?listId,
        }),
      );
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // --- Pseudo-anonymous device (LGPD consent, login-free) -----------------

  /// Records this device's consent so the server may store its data (the basis
  /// for cloud-saved lists and, later, discount alerts).
  Future<void> registerConsent(String deviceToken, String policyVersion) async {
    final uri = Uri.parse('$_baseUrl/api/v1/device/consent');
    final resp = await _client.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        deviceTokenHeader: deviceToken,
      },
      body: jsonEncode({'accepted': true, 'policy_version': policyVersion}),
    ).timeout(_timeout);
    if (resp.statusCode != 200) {
      _throwHttp('Não foi possível salvar sua preferência.', resp);
    }
  }

  /// LGPD erasure: deletes everything the server holds for this device.
  Future<void> deleteDevice(String deviceToken) async {
    final uri = Uri.parse('$_baseUrl/api/v1/device/me');
    final resp = await _client.delete(
      uri,
      headers: {deviceTokenHeader: deviceToken},
    ).timeout(_timeout);
    if (resp.statusCode != 200) {
      _throwHttp('Não foi possível apagar seus dados.', resp);
    }
  }
}
