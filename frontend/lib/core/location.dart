import 'package:geolocator/geolocator.dart';

/// Where to search from. [approximate] is true when we fell back to a default
/// (location denied/unavailable, or the user is outside Alagoas).
class SearchOrigin {
  final double latitude;
  final double longitude;
  final bool approximate;
  const SearchOrigin(this.latitude, this.longitude, {this.approximate = false});
}

/// A busy, central Maceió neighborhood (Pajuçara / orla) used as the default
/// origin so the app is useful even without a real location fix.
const SearchOrigin kMaceioDefault =
    SearchOrigin(-9.6633, -35.7089, approximate: true);

/// Generous bounding box for the state of Alagoas.
bool _inAlagoas(double lat, double lon) =>
    lat <= -8.75 && lat >= -11.0 && lon <= -35.0 && lon >= -38.3;

class LocationService {
  /// Resolves the search origin. Never throws: any failure, denial, timeout, or
  /// an out-of-state position falls back to [kMaceioDefault].
  Future<SearchOrigin> resolveOrigin() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return kMaceioDefault;

      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) {
        return kMaceioDefault;
      }

      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 8),
        ),
      );
      if (_inAlagoas(pos.latitude, pos.longitude)) {
        return SearchOrigin(pos.latitude, pos.longitude);
      }
      return kMaceioDefault; // user is outside Alagoas
    } catch (_) {
      return kMaceioDefault;
    }
  }
}
