"""SearchRequest coordinate sanity (issue #334)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.search import SearchRequest


def test_maceio_coords_ok():
    req = SearchRequest(items=["arroz"], latitude=-9.6633, longitude=-35.7089)
    assert req.latitude == pytest.approx(-9.6633)
    assert req.longitude == pytest.approx(-35.7089)


def test_omit_coords_ok():
    req = SearchRequest(items=["arroz"])
    assert req.latitude is None
    assert req.longitude is None


def test_zero_zero_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(items=["arroz"], latitude=0.0, longitude=0.0)


def test_only_latitude_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(items=["arroz"], latitude=-9.66)


def test_nan_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(items=["arroz"], latitude=float("nan"), longitude=-35.7)


def test_pacific_rejected():
    with pytest.raises(ValidationError):
        SearchRequest(items=["arroz"], latitude=37.77, longitude=-122.42)
