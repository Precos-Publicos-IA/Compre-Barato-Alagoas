/// Lightweight pt-BR formatting (avoids pulling in intl for v1).
library;

String formatBRL(num value) {
  final negative = value < 0;
  final cents = (value.abs() * 100).round();
  final reais = (cents ~/ 100).toString();
  final frac = (cents % 100).toString().padLeft(2, '0');

  // Group thousands with dots.
  final buf = StringBuffer();
  for (var i = 0; i < reais.length; i++) {
    if (i > 0 && (reais.length - i) % 3 == 0) buf.write('.');
    buf.write(reais[i]);
  }
  return '${negative ? '-' : ''}R\$ $buf,$frac';
}

/// e.g. "R$ 4,98 / kg" — the fair-comparison number.
String formatUnitPrice(num unitPrice, String baseUnit) {
  return '${formatBRL(unitPrice)} / $baseUnit';
}

String formatDistance(double? km) {
  if (km == null) return '';
  if (km < 1) return '${(km * 1000).round()} m';
  return '${km.toStringAsFixed(1)} km';
}

/// Fixed offset for America/Maceio (Alagoas) and most of Brazil: UTC−3.
/// Brazil no longer observes DST (since 2019), so a constant offset is accurate
/// without pulling in `intl` / timezone databases for v1.
const Duration kBrazilUtcOffset = Duration(hours: -3);

/// Converts an instant to the Brazil (Maceió) civil calendar date.
///
/// Exposed for unit tests so we prove the shipped offset logic, not a reimplementation.
DateTime brazilCivilDateTime(DateTime instant) {
  final utc = instant.isUtc ? instant : instant.toUtc();
  return utc.add(kBrazilUtcOffset);
}

/// "03/06/2026" from an ISO timestamp. Empty for null/invalid input.
///
/// SEFAZ `dataVenda` is shown to users in Alagoas; instants in UTC (or with an
/// offset) are converted to **America/Maceio (UTC−3)** before taking Y/M/D so
/// late-evening UTC does not display as the next calendar day on iPhone/device
/// clocks set to Brazil (issue #59).
///
/// Date-only strings (`2026-06-05`) have no time zone; the calendar day is kept
/// as written (typical for pure sale dates without a time component).
String formatDate(String? iso) {
  if (iso == null || iso.isEmpty) return '';
  final trimmed = iso.trim();
  final dt = DateTime.tryParse(trimmed);
  if (dt == null) return '';
  String two(int n) => n.toString().padLeft(2, '0');

  final hasTime = trimmed.contains('T') ||
      RegExp(r'\d{4}-\d{2}-\d{2}\s+\d').hasMatch(trimmed);
  final civil = hasTime ? brazilCivilDateTime(dt) : dt;
  return '${two(civil.day)}/${two(civil.month)}/${civil.year}';
}
