"""ETA along a route and reading the forecast at the moment the truck is there (SPEC §3.3)."""

from datetime import UTC, datetime, timedelta

import pytest

from trips.domain.eta import time_at_mile
from trips.domain.models import LatLon
from trips.domain.weather import HourlyForecast

T0 = datetime(2026, 11, 3, 0, 0, tzinfo=UTC)


def forecast(**overrides: list[float | None]) -> HourlyForecast:
    hours = 4
    series: dict[str, list[float | None]] = {
        "wind": [10.0, 20.0, 30.0, 40.0],
        "gust": [15.0, 25.0, 35.0, 45.0],
        "rain": [0.0, 0.1, 0.2, 0.3],
        "showers": [0.0, 0.0, 0.05, 0.0],
        "snow": [0.0, 0.0, 0.0, 1.0],
    }
    series.update(overrides)
    assert all(len(v) == hours for v in series.values())
    return HourlyForecast(cell=LatLon(40, -105), start_utc=T0, **series)


def test_time_at_mile_interpolates_cumulative_seconds() -> None:
    assert time_at_mile([0, 10, 30], [0, 600, 1800], 20) == pytest.approx(1200)


def test_time_at_mile_clamps_beyond_the_route() -> None:
    assert time_at_mile([0, 10], [0, 600], 50) == 600


def test_wind_is_interpolated_between_hourly_stamps() -> None:
    w = forecast().weather_at(T0 + timedelta(minutes=90))

    assert w is not None
    assert w.wind_mph == pytest.approx(25.0)


def test_precipitation_is_the_hour_the_truck_is_in_not_interpolated() -> None:
    # 01:30 is inside the 01:00–02:00 hour, whose total Open-Meteo stamps at 02:00.
    w = forecast().weather_at(T0 + timedelta(minutes=90))

    assert w is not None
    assert w.rain_in_hr == pytest.approx(0.2 + 0.05)  # rain + showers
    assert w.snow_in_hr == 0.0
    assert w.gust_mph == 35.0


def test_on_the_hour_uses_the_hour_that_starts_then() -> None:
    w = forecast().weather_at(T0 + timedelta(hours=2))

    assert w is not None
    assert w.wind_mph == 30.0
    assert w.rain_in_hr == pytest.approx(0.3)
    assert w.snow_in_hr == 1.0


def test_times_outside_the_forecast_are_unknown() -> None:
    assert forecast().weather_at(T0 - timedelta(minutes=1)) is None
    assert forecast().weather_at(T0 + timedelta(hours=3)) is None  # its hour total is past the data


def test_missing_values_in_the_series_are_unknown() -> None:
    f = forecast(wind=[10.0, None, 30.0, 40.0])

    assert f.weather_at(T0 + timedelta(minutes=30)) is None


def test_a_missing_gust_does_not_hide_the_weather_that_is_scored() -> None:
    w = forecast(gust=[15.0, None, 35.0, 45.0]).weather_at(T0 + timedelta(minutes=30))

    assert w is not None
    assert w.wind_mph == pytest.approx(15.0)
    assert w.gust_mph is None
