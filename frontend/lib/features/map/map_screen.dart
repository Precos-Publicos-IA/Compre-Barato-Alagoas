import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../core/format.dart';
import '../../data/models.dart';

/// Shows the ranked stores on an OpenStreetMap (no API key required).
class MapScreen extends StatelessWidget {
  const MapScreen({super.key, required this.response});

  final SearchResponse response;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final stores = response.stores
        .where((s) => s.latitude != null && s.longitude != null)
        .toList();
    final origin = LatLng(response.originLat, response.originLon);

    return Scaffold(
      appBar: AppBar(title: const Text('Mapa das lojas')),
      body: FlutterMap(
        options: MapOptions(initialCenter: origin, initialZoom: 12.5),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'br.ia.precospublicos.compre_barato_alagoas',
          ),
          MarkerLayer(
            markers: [
              Marker(
                point: origin,
                width: 40,
                height: 40,
                child: Icon(Icons.my_location, color: scheme.tertiary, size: 32),
              ),
              for (var i = 0; i < stores.length; i++)
                Marker(
                  point: LatLng(stores[i].latitude!, stores[i].longitude!),
                  width: 160,
                  height: 64,
                  child: _StorePin(store: stores[i], best: i == 0),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StorePin extends StatelessWidget {
  const _StorePin({required this.store, required this.best});
  final StoreResult store;
  final bool best;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: best ? scheme.primary : Colors.white,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: scheme.primary),
          ),
          child: Text(
            formatBRL(store.total),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: best ? Colors.white : scheme.primary,
            ),
          ),
        ),
        Icon(Icons.location_on,
            color: best ? scheme.primary : Colors.redAccent, size: 28),
      ],
    );
  }
}
