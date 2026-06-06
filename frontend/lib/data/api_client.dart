import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import 'models.dart';

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

/// Thin HTTP client for the Compre Barato Alagoas backend.
class ApiClient {
  ApiClient({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = baseUrl ?? AppConfig.apiBaseUrl;

  final http.Client _client;
  final String _baseUrl;

  Future<List<Suggestion>> fetchSuggestions() async {
    final uri = Uri.parse('$_baseUrl/api/v1/suggestions');
    final resp = await _client.get(uri);
    if (resp.statusCode != 200) {
      throw ApiException('Falha ao carregar sugestões (${resp.statusCode})');
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
    final resp = await _client.get(uri);
    if (resp.statusCode == 404) return null;
    if (resp.statusCode != 200) {
      throw ApiException('Não foi possível abrir a lista compartilhada.');
    }
    final body = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return (body['items'] as List<dynamic>).map((e) => e as String).toList();
  }

  /// Header carrying the pseudo-anonymous device token (a bearer credential).
  static const String deviceTokenHeader = 'X-Device-Token';

  Future<SearchResponse> search(
    List<String> items, {
    double? latitude,
    double? longitude,
    int? radiusKm,
    int? days,
    String? deviceToken,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/v1/search');
    final payload = <String, dynamic>{
      'items': items,
      'latitude': ?latitude,
      'longitude': ?longitude,
      'radius_km': ?radiusKm,
      'days': ?days,
    };
    final resp = await _client.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        // Sent only when the user opted into cloud sync, so consented devices
        // get this list saved to their server-side history.
        deviceTokenHeader: ?deviceToken,
      },
      body: jsonEncode(payload),
    );
    if (resp.statusCode == 429) {
      throw ApiException('Você atingiu o limite de buscas de hoje.');
    }
    if (resp.statusCode != 200) {
      throw ApiException('Não foi possível buscar os preços agora.');
    }
    final body = jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return SearchResponse.fromJson(body);
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
    );
    if (resp.statusCode != 200) {
      throw ApiException('Não foi possível salvar sua preferência.');
    }
  }

  /// LGPD erasure: deletes everything the server holds for this device.
  Future<void> deleteDevice(String deviceToken) async {
    final uri = Uri.parse('$_baseUrl/api/v1/device/me');
    final resp = await _client.delete(
      uri,
      headers: {deviceTokenHeader: deviceToken},
    );
    if (resp.statusCode != 200) {
      throw ApiException('Não foi possível apagar seus dados.');
    }
  }
}
