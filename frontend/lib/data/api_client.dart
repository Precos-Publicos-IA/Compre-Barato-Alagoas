import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import 'models.dart';

class ApiException implements Exception {
  final String message;

  /// Server `X-Request-ID` when present — helps support correlate logs/Sentry (#136).
  final String? requestId;

  /// HTTP status when the failure came from a response (e.g. 400 malformed list).
  final int? statusCode;

  ApiException(this.message, {this.requestId, this.statusCode});

  /// Malformed share id (server rejects non-hex list_id) (#390 / #381).
  bool get isInvalidListId => statusCode == 400;

  @override
  String toString() {
    final id = requestId?.trim();
    if (id == null || id.isEmpty) return message;
    return '$message (ref: $id)';
  }
}

/// Outcome of [ApiClient.submitFeedback] — success or failure with optional ref (#396).
class FeedbackSubmitResult {
  const FeedbackSubmitResult._({
    required this.ok,
    this.requestId,
    this.statusCode,
  });

  final bool ok;
  final String? requestId;
  final int? statusCode;

  factory FeedbackSubmitResult.success({String? requestId}) =>
      FeedbackSubmitResult._(ok: true, requestId: requestId);

  factory FeedbackSubmitResult.failure({String? requestId, int? statusCode}) =>
      FeedbackSubmitResult._(
        ok: false,
        requestId: requestId,
        statusCode: statusCode,
      );
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
      throw ApiException(
        message,
        requestId: requestIdOf(resp),
        statusCode: resp.statusCode,
      );

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
  /// expired or doesn't exist (HTTP 404). Throws [ApiException] with
  /// [ApiException.isInvalidListId] on HTTP 400 (malformed id, #390).
  Future<List<String>?> fetchList(String listId) async {
    final uri = Uri.parse('$_baseUrl/api/v1/lists/$listId');
    final resp = await _get(uri);
    if (resp.statusCode == 404) return null;
    if (resp.statusCode == 400) {
      _throwHttp('Este link não é válido.', resp);
    }
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
  }) async {
    final uri = Uri.parse('$_baseUrl/api/v1/search');
    final payload = <String, dynamic>{
      'items': items,
      'latitude': ?latitude,
      'longitude': ?longitude,
      'radius_km': ?radiusKm,
      'days': ?days,
      if (excludedCnpjs.isNotEmpty) 'excluded_cnpjs': excludedCnpjs,
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

  /// Sends user feedback on results (👍/👎 or "item errado"). Best-effort and
  /// anonymous by default; optional device/analytics headers when caller passes
  /// them (#354 / #396). Never throws — returns [FeedbackSubmitResult].
  Future<FeedbackSubmitResult> submitFeedback({
    required String kind,
    bool? helpful,
    String? item,
    String? note,
    String? listId,
    String? deviceToken,
    String? analyticsId,
  }) async {
    try {
      final uri = Uri.parse('$_baseUrl/api/v1/feedback');
      final resp = await _post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          deviceTokenHeader: ?deviceToken,
          analyticsIdHeader: ?analyticsId,
        },
        body: jsonEncode({
          'kind': kind,
          'helpful': ?helpful,
          'item': ?item,
          'note': ?note,
          'list_id': ?listId,
        }),
      );
      final rid = requestIdOf(resp);
      if (resp.statusCode == 200) {
        return FeedbackSubmitResult.success(requestId: rid);
      }
      return FeedbackSubmitResult.failure(
        requestId: rid,
        statusCode: resp.statusCode,
      );
    } on TimeoutException {
      return const FeedbackSubmitResult._(ok: false);
    } on http.ClientException {
      return const FeedbackSubmitResult._(ok: false);
    } catch (_) {
      return const FeedbackSubmitResult._(ok: false);
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
