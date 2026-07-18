import '../../data/models.dart';

/// Minimum basket coverage to show primary “economize R$” hero / share claim.
/// Below this, UI must not present partial baskets as a complete savings win.
const double kPrimarySavingsCoverageThreshold = 0.7;

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

/// Best-store basket coverage for honesty gates on savings UI.
class BasketCoverage {
  /// Max [StoreResult.itemsFound] among compared stores.
  final int found;

  /// Basket size ([StoreResult.itemsTotal]); consistent across the result set.
  final int total;

  const BasketCoverage({required this.found, required this.total});

  double get fraction => total <= 0 ? 0.0 : found / total;

  /// Every requested item has a price on the best store.
  bool get isComplete => total > 0 && found >= total;

  /// High enough to claim “economize R$ X” as the primary hero / share line.
  /// True when complete **or** coverage ≥ [kPrimarySavingsCoverageThreshold].
  bool get allowsPrimarySavings =>
      isComplete || fraction >= kPrimarySavingsCoverageThreshold;

  /// Honest partial-hero title, e.g. “Encontramos 4 de 10 itens”.
  String get partialHeroTitle {
    if (total <= 0) return 'Nenhum item encontrado';
    return 'Encontramos $found de $total itens';
  }

  /// Secondary honest copy under the partial hero.
  String get partialHeroSubtitle =>
      'Compare só o que tem preço — a economia total da lista pode ser maior.';
}

/// Coverage from the store that found the most items (best available basket).
BasketCoverage computeCoverage(List<StoreResult> stores) {
  if (stores.isEmpty) {
    return const BasketCoverage(found: 0, total: 0);
  }
  final maxFound =
      stores.map((s) => s.itemsFound).reduce((a, b) => a > b ? a : b);
  final total =
      stores.map((s) => s.itemsTotal).reduce((a, b) => a > b ? a : b);
  return BasketCoverage(found: maxFound, total: total);
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

/// Whether the primary savings hero (and “compartilhar economia” claim) is OK.
bool shouldShowPrimarySavings(
  SavingsInfo? savings,
  BasketCoverage coverage,
) {
  return savings != null &&
      savings.amount > 0 &&
      coverage.allowsPrimarySavings;
}
