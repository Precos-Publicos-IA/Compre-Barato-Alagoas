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

/// Returns null when there are not at least two stores on equal item-count
/// footing, or when the price gap is zero (#410).
SavingsInfo? computeSavings(List<StoreResult> stores) {
  if (stores.isEmpty) return null;
  final maxFound =
      stores.map((s) => s.itemsFound).reduce((a, b) => a > b ? a : b);
  final comparable = stores.where((s) => s.itemsFound == maxFound).toList();
  if (comparable.length < 2) return null;
  final cheapest =
      comparable.reduce((a, b) => a.total <= b.total ? a : b);
  final priciest =
      comparable.reduce((a, b) => a.total >= b.total ? a : b);
  final amount = priciest.total - cheapest.total;
  if (amount <= 0) return null;
  return SavingsInfo(
    amount: amount,
    cheapest: cheapest,
    comparedStores: comparable.length,
  );
}
