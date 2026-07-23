/// Pure helpers for wrong_item feedback payloads (Phase 6).
///
/// Keeps query + product description extraction testable without widget trees.
library;

import '../../data/models.dart';

/// First non-empty product description per user query from search results.
///
/// Walks stores in order (caller should pass cheapest-first / display order so
/// the top/selected line is preferred). Only [ItemOffer.found] lines with a
/// non-empty [ItemOffer.description] contribute.
Map<String, String> itemDescriptionsFromResults(
  List<StoreResult> stores, {
  List<String>? preferredQueries,
}) {
  final byQueryLower = <String, String>{};
  final byQueryExact = <String, String>{};

  for (final store in stores) {
    for (final offer in store.items) {
      if (!offer.found) continue;
      final desc = offer.description?.trim();
      if (desc == null || desc.isEmpty) continue;
      final q = offer.query.trim();
      if (q.isEmpty) continue;
      byQueryExact.putIfAbsent(q, () => desc);
      byQueryLower.putIfAbsent(q.toLowerCase(), () => desc);
    }
  }

  if (preferredQueries == null || preferredQueries.isEmpty) {
    return Map<String, String>.from(byQueryExact);
  }

  final out = <String, String>{};
  for (final raw in preferredQueries) {
    final item = raw.trim();
    if (item.isEmpty) continue;
    final hit = byQueryExact[item] ?? byQueryLower[item.toLowerCase()];
    if (hit != null && hit.isNotEmpty) {
      out[raw] = hit;
    }
  }
  return out;
}

/// JSON body fields for POST /api/v1/feedback kind=wrong_item.
///
/// Always includes [query] (and legacy [item]) when non-empty. Includes
/// [description] when non-empty so learn_policy can demote the bad mapping.
Map<String, dynamic> wrongItemFeedbackBody({
  required String query,
  String? description,
  String? note,
  String? listId,
}) {
  final q = query.trim();
  final d = description?.trim();
  final n = note?.trim();
  final lid = listId?.trim();
  return <String, dynamic>{
    'kind': 'wrong_item',
    if (q.isNotEmpty) 'query': q,
    if (q.isNotEmpty) 'item': q,
    if (d != null && d.isNotEmpty) 'description': d,
    if (n != null && n.isNotEmpty) 'note': n,
    if (lid != null && lid.isNotEmpty) 'list_id': lid,
  };
}
