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

  Future<SearchResponse> search(
    List<String> items, {
    double? latitude,
    double? longitude,
    int? radiusKm,
    int? days,
  }) async {
    final uri = Uri.parse('$_baseUrl/api/v1/search');
    final payload = <String, dynamic>{
      'items': items,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (radiusKm != null) 'radius_km': radiusKm,
      if (days != null) 'days': days,
    };
    final resp = await _client.post(
      uri,
      headers: {'Content-Type': 'application/json'},
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
}
