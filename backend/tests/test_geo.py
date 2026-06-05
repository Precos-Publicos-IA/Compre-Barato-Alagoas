from app.services.geo import haversine_km


def test_zero_distance():
    assert haversine_km(-9.65, -35.71, -9.65, -35.71) == 0.0


def test_known_distance_maceio_arapiraca():
    # Maceió (~-9.65,-35.74) to Arapiraca (~-9.75,-36.66) is ~100 km.
    d = haversine_km(-9.6498, -35.7089, -9.7520, -36.6610)
    assert 95 < d < 110
