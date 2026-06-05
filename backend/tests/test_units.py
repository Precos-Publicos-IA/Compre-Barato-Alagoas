import pytest

from app.services.normalization.units import dimension, is_known_unit, to_base


def test_dimension():
    assert dimension("kg") == "mass"
    assert dimension("ML") == "volume"
    assert dimension("UN") == "count"
    assert dimension("xyz") is None


@pytest.mark.parametrize(
    "value,unit,expected_value,expected_base",
    [
        (5, "kg", 5.0, "kg"),
        (500, "g", 0.5, "kg"),
        (1, "L", 1.0, "L"),
        (900, "ml", 0.9, "L"),
        (12, "un", 12.0, "un"),
        (1, "dz", 12.0, "un"),
    ],
)
def test_to_base(value, unit, expected_value, expected_base):
    got = to_base(value, unit)
    assert got is not None
    assert got[0] == pytest.approx(expected_value)
    assert got[1] == expected_base


def test_to_base_unknown():
    assert to_base(1, "blah") is None
    assert not is_known_unit("blah")
