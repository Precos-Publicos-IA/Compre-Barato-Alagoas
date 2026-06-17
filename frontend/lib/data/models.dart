/// Data models mirroring the backend's `/api/v1/search` response.
library;

class Suggestion {
  final String label;
  final String emoji;
  const Suggestion({required this.label, required this.emoji});

  factory Suggestion.fromJson(Map<String, dynamic> j) => Suggestion(
        label: j['label'] as String,
        emoji: (j['emoji'] as String?) ?? '',
      );
}

class ItemOffer {
  final String query;
  final bool found;
  final String? description;
  final double? price;
  final double? unitPrice;
  final String? baseUnit;
  final double? quantity;
  final String? unit;

  /// ISO timestamp of the sale that set this price (SEFAZ `dataVenda`).
  final String? saleDate;
  final bool quantityParsed;

  /// How many of this item the user asked for ("3 arroz" -> 3). Defaults to 1.
  final int requestedQuantity;

  /// price * requestedQuantity (what the line actually costs).
  final double? lineTotal;

  const ItemOffer({
    required this.query,
    required this.found,
    this.description,
    this.price,
    this.unitPrice,
    this.baseUnit,
    this.quantity,
    this.unit,
    this.saleDate,
    this.quantityParsed = false,
    this.requestedQuantity = 1,
    this.lineTotal,
  });

  factory ItemOffer.fromJson(Map<String, dynamic> j) => ItemOffer(
        query: j['query'] as String,
        found: j['found'] as bool? ?? false,
        description: j['description'] as String?,
        price: (j['price'] as num?)?.toDouble(),
        unitPrice: (j['unit_price'] as num?)?.toDouble(),
        baseUnit: j['base_unit'] as String?,
        quantity: (j['quantity'] as num?)?.toDouble(),
        unit: j['unit'] as String?,
        saleDate: j['sale_date'] as String?,
        quantityParsed: j['quantity_parsed'] as bool? ?? false,
        requestedQuantity: (j['requested_quantity'] as num?)?.toInt() ?? 1,
        lineTotal: (j['line_total'] as num?)?.toDouble(),
      );
}

class StoreResult {
  final String cnpj;
  final String name;
  final double? latitude;
  final double? longitude;
  final String? address;
  final String? bairro;
  final double? distanceKm;
  final int itemsFound;
  final int itemsTotal;
  final double total;
  final List<ItemOffer> items;
  final List<String> missing;

  const StoreResult({
    required this.cnpj,
    required this.name,
    this.latitude,
    this.longitude,
    this.address,
    this.bairro,
    this.distanceKm,
    required this.itemsFound,
    required this.itemsTotal,
    required this.total,
    required this.items,
    required this.missing,
  });

  factory StoreResult.fromJson(Map<String, dynamic> j) => StoreResult(
        cnpj: j['cnpj'] as String,
        name: j['name'] as String,
        latitude: (j['latitude'] as num?)?.toDouble(),
        longitude: (j['longitude'] as num?)?.toDouble(),
        address: j['address'] as String?,
        bairro: j['bairro'] as String?,
        distanceKm: (j['distance_km'] as num?)?.toDouble(),
        itemsFound: j['items_found'] as int,
        itemsTotal: j['items_total'] as int,
        total: (j['total'] as num).toDouble(),
        items: (j['items'] as List<dynamic>)
            .map((e) => ItemOffer.fromJson(e as Map<String, dynamic>))
            .toList(),
        missing:
            (j['missing'] as List<dynamic>? ?? []).map((e) => e as String).toList(),
      );
}

class SearchMetrics {
  final int itemsRequested;
  final int storesFound;
  final double matchRate;
  final double quantityParseRate;

  const SearchMetrics({
    required this.itemsRequested,
    required this.storesFound,
    required this.matchRate,
    required this.quantityParseRate,
  });

  factory SearchMetrics.fromJson(Map<String, dynamic> j) => SearchMetrics(
        itemsRequested: j['items_requested'] as int,
        storesFound: j['stores_found'] as int,
        matchRate: (j['match_rate'] as num).toDouble(),
        quantityParseRate: (j['quantity_parse_rate'] as num).toDouble(),
      );
}

class SearchResponse {
  final double originLat;
  final double originLon;
  final int radiusKm;
  final int days;
  final int itemsRequested;
  final String dataSource;

  /// Shareable UUID for this shopping list (null if storage was unavailable).
  final String? listId;
  final List<StoreResult> stores;
  final SearchMetrics metrics;

  const SearchResponse({
    required this.originLat,
    required this.originLon,
    required this.radiusKm,
    required this.days,
    required this.itemsRequested,
    required this.dataSource,
    this.listId,
    required this.stores,
    required this.metrics,
  });

  factory SearchResponse.fromJson(Map<String, dynamic> j) => SearchResponse(
        originLat: (j['origin']['latitude'] as num).toDouble(),
        originLon: (j['origin']['longitude'] as num).toDouble(),
        radiusKm: j['radius_km'] as int,
        days: j['days'] as int,
        itemsRequested: j['items_requested'] as int,
        dataSource: j['data_source'] as String,
        listId: j['list_id'] as String?,
        stores: (j['stores'] as List<dynamic>)
            .map((e) => StoreResult.fromJson(e as Map<String, dynamic>))
            .toList(),
        metrics: SearchMetrics.fromJson(j['metrics'] as Map<String, dynamic>),
      );
}
