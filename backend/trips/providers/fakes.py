"""Deterministic stand-ins for the third-party services, used by the test suite.

`RecordedRouting` replays a real Valhalla response. `SyntheticWeather` produces an exact,
known forecast so assertions can name the level each checkpoint must get.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from trips.domain.models import LatLon, Place, Route
from trips.domain.weather import HourlyForecast
from trips.providers.valhalla import LABELS, _parse_trip


class RecordedRouting:
    name = "recorded"

    def __init__(self, fixture: Path, error: Exception | None = None) -> None:
        self.payload = json.loads(fixture.read_text())
        self.error = error

    async def routes(self, origin: Place, destination: Place, gross_lb: int) -> list[Route]:
        if self.error:
            raise self.error
        trips = [self.payload["trip"]] + [a["trip"] for a in self.payload.get("alternates", [])]
        return [_parse_trip(t, i) for i, t in enumerate(trips[: len(LABELS)])]


class SyntheticWeather:
    """Calm and dry everywhere except where `windy(cell)` is true; `missing(cell)` simulates failures."""

    name = "synthetic"

    def __init__(
        self,
        windy: Callable[[LatLon], bool] = lambda c: c.lat > 41.0,
        wind_mph: float = 40.0,
        calm_mph: float = 8.0,
        missing: Callable[[LatLon], bool] = lambda c: False,
    ) -> None:
        self.windy, self.wind_mph, self.calm_mph, self.missing = windy, wind_mph, calm_mph, missing
        self.requested: list[LatLon] = []

    async def hourly(
        self, cells: list[LatLon], start_utc: datetime, end_utc: datetime
    ) -> dict[LatLon, HourlyForecast]:
        self.requested.extend(cells)
        hours = int((end_utc - start_utc) / timedelta(hours=1)) + 1
        out = {}
        for c in cells:
            if self.missing(c):
                continue
            wind = self.wind_mph if self.windy(c) else self.calm_mph
            out[c] = HourlyForecast(
                cell=c,
                start_utc=start_utc,
                wind=[wind] * hours,
                gust=[wind + 10] * hours,
                rain=[0.0] * hours,
                showers=[0.0] * hours,
                snow=[0.0] * hours,
            )
        return out


class FixedGeocoder:
    name = "fixed"

    def __init__(self, places: list[Place]) -> None:
        self.places = places

    async def suggest(self, q: str, at: LatLon | None, limit: int) -> list[Place]:
        return [p for p in self.places if q.lower() in p.label.lower()][:limit]
