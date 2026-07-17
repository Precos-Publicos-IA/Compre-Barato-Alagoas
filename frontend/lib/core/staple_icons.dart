import 'package:flutter/material.dart';

/// Material icon for a staple grocery label.
///
/// Avoids emoji tofu (□) on web/Android builds where emoji fonts fail.
/// Falls back to a generic grocery icon when the label is unknown.
IconData stapleIconFor(String label) {
  final key = _normalize(label);
  return _map[key] ?? Icons.shopping_basket_outlined;
}

String _normalize(String label) {
  var s = label.trim().toLowerCase();
  const accents = {
    'á': 'a',
    'à': 'a',
    'ã': 'a',
    'â': 'a',
    'é': 'e',
    'ê': 'e',
    'í': 'i',
    'ó': 'o',
    'ô': 'o',
    'õ': 'o',
    'ú': 'u',
    'ç': 'c',
  };
  for (final e in accents.entries) {
    s = s.replaceAll(e.key, e.value);
  }
  return s;
}

const _map = <String, IconData>{
  'arroz': Icons.restaurant_outlined,
  'feijao': Icons.spa_outlined,
  'leite': Icons.local_drink_outlined,
  'ovo': Icons.egg_outlined,
  'ovos': Icons.egg_outlined,
  'acucar': Icons.cake_outlined,
  'cafe': Icons.coffee_outlined,
  'oleo': Icons.water_drop_outlined,
  'macarrao': Icons.ramen_dining_outlined,
  'banana': Icons.eco_outlined,
  'tomate': Icons.local_florist_outlined,
  'frango': Icons.set_meal_outlined,
  'refrigerante': Icons.sports_bar_outlined,
  'pao': Icons.bakery_dining_outlined,
  'pao frances': Icons.bakery_dining_outlined,
  'manteiga': Icons.breakfast_dining_outlined,
  'queijo': Icons.lunch_dining_outlined,
  'carne': Icons.set_meal_outlined,
  'carne moida': Icons.set_meal_outlined,
  'batata': Icons.grass_outlined,
  'cebola': Icons.grass_outlined,
  'alho': Icons.grass_outlined,
  'sabao': Icons.cleaning_services_outlined,
  'detergente': Icons.cleaning_services_outlined,
  'agua': Icons.water_drop_outlined,
  'suco': Icons.local_bar_outlined,
  'biscoito': Icons.cookie_outlined,
  'bolacha': Icons.cookie_outlined,
  'farinha': Icons.grain_outlined,
  'sal': Icons.grain_outlined,
  'vinagre': Icons.water_drop_outlined,
  'margarina': Icons.breakfast_dining_outlined,
  'iogurte': Icons.icecream_outlined,
  'presunto': Icons.lunch_dining_outlined,
  'salsicha': Icons.lunch_dining_outlined,
  'linguiça': Icons.lunch_dining_outlined,
  'linguica': Icons.lunch_dining_outlined,
  'peixe': Icons.set_meal_outlined,
  'alface': Icons.eco_outlined,
  'cenoura': Icons.eco_outlined,
  'laranja': Icons.eco_outlined,
  'maca': Icons.eco_outlined,
  'maçã': Icons.eco_outlined,
  'uva': Icons.eco_outlined,
  'melancia': Icons.eco_outlined,
  'abóbora': Icons.eco_outlined,
  'abobora': Icons.eco_outlined,
};
