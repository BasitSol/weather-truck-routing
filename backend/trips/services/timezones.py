"""IANA timezone at a point, so every ETA can be shown in the local time of that place (D14)."""

from __future__ import annotations

from functools import cache

from timezonefinder import TimezoneFinder

from trips.domain.geo import snap
from trips.domain.models import LatLon


@cache
def _finder() -> TimezoneFinder:
    return TimezoneFinder(in_memory=True)


@cache
def _tz_for_cell(cell: LatLon) -> str:
    return _finder().timezone_at(lng=cell.lon, lat=cell.lat) or "UTC"


def tz_at(pos: LatLon) -> str:
    return _tz_for_cell(snap(pos))
