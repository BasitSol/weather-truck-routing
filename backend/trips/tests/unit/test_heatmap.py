"""Corridor heat: points along every route, 0–48 h of levels from departure."""

from datetime import UTC, datetime, timedelta

from trips.domain.geo import cumulative_miles
from trips.domain.heatmap import HEAT_HOURS, corridor_points, heat_series
from trips.domain.models import LatLon, Level, Route
from trips.domain.weather import HourlyForecast

T0 = datetime(2026, 11, 3, tzinfo=UTC)


def straight_route(rid: str, lon: float) -> Route:
    pts = [LatLon(39.0 + i * 0.1, lon) for i in range(30)]  # ~200 mi due north
    cum = cumulative_miles(pts)
    return Route(
        id=rid,
        label=rid,
        points=pts,
        cum_mi=cum,
        cum_s=[c * 60 for c in cum],
        length_mi=cum[-1],
        duration_s=cum[-1] * 60,
    )


def test_corridor_points_follow_each_route_at_the_spacing() -> None:
    pts = corridor_points([straight_route("r1", -105.0)], spacing_mi=10)

    assert 19 <= len(pts) <= 22
    assert all(p.lon == -105.0 for p in pts)


def test_overlapping_routes_share_corridor_cells() -> None:
    one = corridor_points([straight_route("r1", -105.0)], spacing_mi=10)
    both = corridor_points([straight_route("r1", -105.0), straight_route("r2", -105.01)], spacing_mi=10)

    assert len(both) == len(one)


def test_corridor_points_are_capped_per_route() -> None:
    pts = corridor_points([straight_route("r1", -105.0)], spacing_mi=1, cap=50)

    assert len(pts) <= 50


def test_heat_series_has_one_level_per_hour_inclusive_of_hour_48() -> None:
    hours = 60
    f = HourlyForecast(
        cell=LatLon(40, -105),
        start_utc=T0,
        wind=[40.0] * hours,
        gust=[50.0] * hours,
        rain=[0.0] * hours,
        showers=[0.0] * hours,
        snow=[0.0] * hours,
    )

    light = heat_series(f, T0, load_lb=20_000)
    heavy = heat_series(f, T0, load_lb=45_000)

    assert HEAT_HOURS == 48
    assert len(light) == 49
    assert set(light) == {Level.HIGH}
    assert set(heavy) == {Level.SEVERE}  # same classifier, same load rules as checkpoints


def test_heat_series_is_unknown_beyond_the_forecast_and_without_a_forecast() -> None:
    f = HourlyForecast(
        cell=LatLon(40, -105),
        start_utc=T0,
        wind=[5.0] * 10,
        gust=[5.0] * 10,
        rain=[0.0] * 10,
        showers=[0.0] * 10,
        snow=[0.0] * 10,
    )

    series = heat_series(f, T0 + timedelta(hours=2), load_lb=20_000)

    assert series[:7] == [Level.LOW] * 7
    assert series[7:] == [Level.UNKNOWN] * 42
    assert heat_series(None, T0, load_lb=20_000) == [Level.UNKNOWN] * 49
