"""Detour waypoints and the self-overlap check used to find extra route options (D15)."""

import pytest

from trips.domain.geo import cumulative_miles, detour_points, doubles_back, haversine_mi, side_of_line
from trips.domain.models import LatLon, Route

DALLAS = LatLon(32.7767, -96.7970)
HOUSTON = LatLon(29.7604, -95.3698)


def _route(points: list[LatLon]) -> Route:
    cum = cumulative_miles(points)
    return Route("r1", "Route A", points, cum, [m * 60 for m in cum], cum[-1], cum[-1] * 60)


def test_detour_points_sit_either_side_of_the_midpoint_at_the_requested_share_of_the_trip() -> None:
    left, right = detour_points(DALLAS, HOUSTON, 0.12)
    trip = haversine_mi(DALLAS, HOUSTON)
    mid = LatLon((DALLAS.lat + HOUSTON.lat) / 2, (DALLAS.lon + HOUSTON.lon) / 2)

    for p in (left, right):
        assert haversine_mi(mid, p) == pytest.approx(0.12 * trip, rel=0.02)
        # Perpendicular: equally far from both ends.
        assert haversine_mi(DALLAS, p) == pytest.approx(haversine_mi(HOUSTON, p), rel=0.02)
    assert side_of_line(DALLAS, HOUSTON, left) != side_of_line(DALLAS, HOUSTON, right)


def test_side_of_line_names_the_compass_side_of_the_direct_line() -> None:
    # Dallas to Houston runs south-east, so the two sides are roughly west and east.
    left, right = detour_points(DALLAS, HOUSTON, 0.12)
    assert {side_of_line(DALLAS, HOUSTON, left), side_of_line(DALLAS, HOUSTON, right)} == {"west", "east"}
    # East-west trip: the sides are north and south.
    a, b = LatLon(40.0, -105.0), LatLon(40.0, -95.0)
    up, down = detour_points(a, b, 0.2)
    assert {side_of_line(a, b, up), side_of_line(a, b, down)} == {"north", "south"}


def test_a_straight_road_does_not_double_back() -> None:
    line = [LatLon(30.0 + i * 0.05, -95.0) for i in range(60)]  # ~200 mi due north
    assert not doubles_back(_route(line))


def test_an_out_and_back_spur_to_a_waypoint_doubles_back() -> None:
    out = [LatLon(30.0, -95.0 + i * 0.05) for i in range(40)]  # ~120 mi east
    back = list(reversed(out))[1:]  # the same road back west
    north = [LatLon(30.0 + i * 0.05, -95.0) for i in range(1, 40)]
    assert doubles_back(_route(out + back + north))


def test_returning_near_an_earlier_point_only_briefly_is_tolerated() -> None:
    # A road that kinks back past the same spot once (a loop ramp) is not a spur.
    road = [LatLon(30.0 + i * 0.05, -95.0) for i in range(30)]
    road += [LatLon(31.45, -95.0 + 0.001), LatLon(31.45, -95.0 + 0.002)]
    road += [LatLon(31.45 + i * 0.05, -95.0) for i in range(1, 30)]
    assert not doubles_back(_route(road))
