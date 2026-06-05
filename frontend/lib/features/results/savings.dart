import '../../data/models.dart';

/// How much the user saves by picking the cheapest store over the most
/// expensive one — comparing only stores that found the same (largest) number
/// of items, so we're not comparing a full basket against a half-empty one.
class SavingsInfo {
  /// Difference between the priciest and cheapest comparable store.
  final double amount;
  final StoreResult cheapest;

  /// How many stores were compared on equal footing.
  final int comparedStores;

  const SavingsInfo({
    required this.amount,
    required this.cheapest,
    required this.comparedStores,
  });
}

SavingsInfo? computeSavings(List<StoreResult> stores) {
  if (stores.isEmpty) return null;
  final maxFound =
      stores.map((s) => s.itemsFound).reduce((a, b) => a > b ? a : b);
  final comparable = stores.where((s) => s.itemsFound == maxFound).toList();
  final cheapest =
      comparable.reduce((a, b) => a.total <= b.total ? a : b);
  final priciest =
      comparable.reduce((a, b) => a.total >= b.total ? a : b);
  return SavingsInfo(
    amount: priciest.total - cheapest.total,
    cheapest: cheapest,
    comparedStores: comparable.length,
  );
}
