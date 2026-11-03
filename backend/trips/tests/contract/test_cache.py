"""Caching decorators: repeat analyses reuse routes and per-cell forecasts instead of refetching."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from django.core.cache import cache

from trips.domain.models import LatLon, Place
from trips.providers.fakes import FixedGeocoder, RecordedRouting, SyntheticWeather
from trips.services.cache import CachedGeocoder, CachedRouting, CachedWeather

FIXTURE = Path(__file__).parent.parent / "fixtures" / "valhalla_den_slc.json"
DENVER = Place("Denver, CO", 39.7392, -104.9903)
SLC = Place("Salt Lake City, UT", 40.7608, -111.891)
START = datetime(2026, 11, 3, 15, tzinfo=UTC)
END = START + timedelta(hours=10)


@pytest.fixture(autouse=True)
def _clean_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


class CountingRouting(RecordedRouting):
    calls = 0

    async def routes(self, origin, destination, gross_lb):  # type: ignore[no-untyped-def]
        self.calls += 1
        return await super().routes(origin, destination, gross_lb)


async def test_the_same_trip_and_weight_is_routed_once() -> None:
    inner = CountingRouting(FIXTURE)
    routing = CachedRouting(inner, ttl_s=600)

    first = await routing.routes(DENVER, SLC, 44_000)
    second = await routing.routes(DENVER, SLC, 44_000)

    assert inner.calls == 1
    assert [r.length_mi for r in first] == [r.length_mi for r in second]


async def test_a_different_weight_is_routed_again_because_truck_restrictions_depend_on_it() -> None:
    inner = CountingRouting(FIXTURE)
    routing = CachedRouting(inner, ttl_s=600)

    await routing.routes(DENVER, SLC, 44_000)
    await routing.routes(DENVER, SLC, 20_000)

    assert inner.calls == 2


async def test_only_cells_missing_from_the_cache_are_fetched() -> None:
    inner = SyntheticWeather()
    weather = CachedWeather(inner, ttl_s=1800)
    a, b, c = LatLon(40.0, -105.0), LatLon(40.05, -105.0), LatLon(40.1, -105.0)

    await weather.hourly([a, b], START, END)
    inner.requested.clear()
    out = await weather.hourly([a, b, c], START, END)

    assert inner.requested == [c]
    assert set(out) == {a, b, c}


async def test_a_different_forecast_window_is_not_served_from_the_cache() -> None:
    inner = SyntheticWeather()
    weather = CachedWeather(inner, ttl_s=1800)
    a = LatLon(40.0, -105.0)

    await weather.hourly([a], START, END)
    inner.requested.clear()
    await weather.hourly([a], START + timedelta(hours=1), END + timedelta(hours=1))

    assert inner.requested == [a]


async def test_missing_cells_are_not_cached_so_a_retry_can_fill_them() -> None:
    a = LatLon(40.0, -105.0)
    weather = CachedWeather(SyntheticWeather(missing=lambda c: True), ttl_s=1800)
    assert await weather.hourly([a], START, END) == {}

    healthy = SyntheticWeather()
    weather.inner = healthy
    assert set(await weather.hourly([a], START, END)) == {a}


async def test_geocode_results_are_cached_but_empty_answers_are_not() -> None:
    slc = Place("Salt Lake City, Utah, US", 40.7608, -111.891)
    geocoder = CachedGeocoder(FixedGeocoder([slc]), ttl_s=86_400)

    assert await geocoder.suggest("salt lake", None, 6) == [slc]
    geocoder.inner = FixedGeocoder([])  # a cached hit must not ask the provider again
    assert await geocoder.suggest("Salt Lake", None, 6) == [slc]
    assert await geocoder.suggest("nowhere", None, 6) == []
    geocoder.inner = FixedGeocoder([Place("Nowhere, US", 1.0, 1.0)])
    assert await geocoder.suggest("nowhere", None, 6) == [Place("Nowhere, US", 1.0, 1.0)]
