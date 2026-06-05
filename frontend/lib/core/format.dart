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

/// "03/06/2026" from an ISO timestamp. Empty for null/invalid input.
/// Uses the recorded (UTC) date so it matches SEFAZ's `dataVenda`.
String formatDate(String? iso) {
  if (iso == null || iso.isEmpty) return '';
  final dt = DateTime.tryParse(iso);
  if (dt == null) return '';
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(dt.day)}/${two(dt.month)}/${dt.year}';
}
