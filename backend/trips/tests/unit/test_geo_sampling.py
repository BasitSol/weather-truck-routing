"""Geometry along a polyline, checkpoint placement and mile ownership."""

import pytest

from trips.domain.geo import (
    cumulative_miles,
    distinct_routes,
    haversine_mi,
    point_at_mile,
    simplify,
    slice_line,
    snap,
)
from trips.domain.models import LatLon, Route
from trips.domain.sampling import checkpoint_miles, owned_miles


def test_haversine_one_degree_of_latitude_is_about_69_miles() -> None:
    assert haversine_mi(LatLon(40, -105), LatLon(41, -105)) == pytest.approx(69.09, abs=0.05)


def test_cumulative_miles_starts_at_zero_and_accumulates() -> None:
    line = [LatLon(40, -105), LatLon(41, -105), LatLon(42, -105)]

    cum = cumulative_miles(line)

    assert cum[0] == 0
    assert cum[1] == pytest.approx(69.09, abs=0.05)
    assert cum[2] == pytest.approx(2 * cum[1], rel=1e-3)


def test_point_at_mile_interpolates_within_a_leg() -> None:
    line = [LatLon(40, -105), LatLon(42, -105)]
    cum = [0.0, 100.0]

    assert point_at_mile(line, cum, 25.0) == LatLon(40.5, -105)


def test_point_at_mile_clamps_to_the_ends() -> None:
    line = [LatLon(40, -105), LatLon(42, -105)]
    cum = [0.0, 100.0]

    assert point_at_mile(line, cum, -5) == LatLon(40, -105)
    assert point_at_mile(line, cum, 500) == LatLon(42, -105)


def test_snap_rounds_to_the_weather_grid() -> None:
    assert snap(LatLon(39.7392, -104.9903)) == LatLon(39.75, -105.0)
    assert snap(LatLon(40.024, -111.026)) == LatLon(40.0, -111.05)


def test_checkpoints_cover_start_every_interval_and_destination() -> None:
    assert checkpoint_miles(100, 25) == [0, 25, 50, 75, 100]
    assert checkpoint_miles(60, 25) == [0, 25, 50, 60]


def test_a_regular_checkpoint_too_close_to_the_destination_is_dropped() -> None:
    # 105 - 100 = 5 < 25/4 → the point at mile 100 is redundant next to the destination.
    assert checkpoint_miles(105, 25) == [0, 25, 50, 75, 105]


def test_short_trips_still_get_start_and_end() -> None:
    assert checkpoint_miles(4, 10) == [0, 4]


@pytest.mark.parametrize("length", [4.0, 37.0, 150.0, 512.4, 1000.0])
@pytest.mark.parametrize("interval", [10, 25, 50])
def test_owned_miles_sum_to_route_length(length: float, interval: int) -> None:
    miles = checkpoint_miles(length, interval)

    assert sum(owned_miles(miles, length)) == pytest.approx(length)


def test_each_checkpoint_owns_half_way_to_its_neighbours() -> None:
    assert owned_miles([0, 25, 50, 60], 60) == [12.5, 25.0, 17.5, 5.0]


def _line(n: int, lon: float = -105.0) -> tuple[list[LatLon], list[float]]:
    pts = [LatLon(40.0 + i * 0.01, lon) for i in range(n)]
    return pts, cumulative_miles(pts)


def test_slice_line_returns_the_stretch_between_two_miles_with_exact_ends() -> None:
    pts, cum = _line(11)  # ~6.9 mi due north

    part = slice_line(pts, cum, 1.0, 3.0)

    assert part[0] == point_at_mile(pts, cum, 1.0)
    assert part[-1] == point_at_mile(pts, cum, 3.0)
    assert all(part[0].lat <= p.lat <= part[-1].lat for p in part)


def test_simplify_drops_collinear_points_but_keeps_corners() -> None:
    straight = [LatLon(40.0 + i * 0.001, -105.0) for i in range(100)]
    corner = [LatLon(40.0, -105.0), LatLon(40.5, -105.0), LatLon(40.5, -104.5)]

    assert simplify(straight) == [straight[0], straight[-1]]
    assert simplify(corner) == corner


def test_near_identical_alternatives_are_dropped() -> None:
    def route(rid: str, lon: float) -> Route:
        pts, cum = _line(200, lon)
        return Route(id=rid, label=rid, points=pts, cum_mi=cum, cum_s=cum, length_mi=cum[-1], duration_s=1)

    kept = distinct_routes([route("a", -105.0), route("b", -105.001), route("c", -105.5)])

    assert [r.id for r in kept] == ["a", "c"]
