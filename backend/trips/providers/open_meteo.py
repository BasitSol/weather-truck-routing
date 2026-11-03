"""Hourly forecasts from Open-Meteo for many grid cells at once.

Requested in the brief's units (mph, inches) and GMT, for exactly the hours the analysis needs.
`precipitation` is deliberately not used: it includes snow water equivalent and would double
count with `snowfall` (which Open-Meteo reports as snow depth).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from trips.domain.models import LatLon
from trips.domain.weather import HourlyForecast
from trips.providers.base import ProviderError, RateLimitedError, client, request_json

log = logging.getLogger(__name__)

HOURLY = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
STAMP = "%Y-%m-%dT%H:%M"


class OpenMeteoWeather:
    name = "open-meteo"

    def __init__(
        self,
        url: str,
        user_agent: str | None = None,
        chunk_size: int = 100,
        concurrency: int = 4,
        backoff_s: float = 0.4,
    ) -> None:
        self.url = url
        self.user_agent = user_agent
        self.chunk_size = chunk_size
        self.concurrency = concurrency
        self.backoff_s = backoff_s

    async def hourly(
        self, cells: list[LatLon], start_utc: datetime, end_utc: datetime
    ) -> dict[LatLon, HourlyForecast]:
        chunks = [cells[i : i + self.chunk_size] for i in range(0, len(cells), self.chunk_size)]
        gate = asyncio.Semaphore(self.concurrency)
        out: dict[LatLon, HourlyForecast] = {}
        throttled: list[RateLimitedError] = []

        async with client(self.user_agent) as http:

            async def fetch(chunk: list[LatLon]) -> None:
                params = {
                    "latitude": ",".join(f"{c.lat:g}" for c in chunk),
                    "longitude": ",".join(f"{c.lon:g}" for c in chunk),
                    "hourly": HOURLY,
                    "wind_speed_unit": "mph",
                    "precipitation_unit": "inch",
                    "timezone": "GMT",
                    "start_hour": start_utc.strftime(STAMP),
                    "end_hour": end_utc.strftime(STAMP),
                }
                async with gate:
                    try:
                        payload = await request_json(
                            http, "GET", self.url, provider=self.name, backoff_s=self.backoff_s, params=params
                        )
                        locations = payload if isinstance(payload, list) else [payload]
                        parsed = {
                            c: _parse_location(c, loc) for c, loc in zip(chunk, locations, strict=False)
                        }
                    except RateLimitedError as exc:
                        throttled.append(exc)
                        return
                    except (
                        ProviderError,
                        httpx.HTTPError,
                        ValueError,
                        KeyError,
                        TypeError,
                        IndexError,
                    ) as exc:
                        log.warning("weather chunk failed (%d cells): %r", len(chunk), exc)
                        return
                out.update(parsed)

            await asyncio.gather(*(fetch(c) for c in chunks))
        if throttled:
            # Throttled cells are not "no forecast"; scoring them as Unknown would skew the ranking.
            log.warning("weather rate-limited: %d of %d chunks refused", len(throttled), len(chunks))
            raise throttled[0]
        return out


def _parse_location(cell: LatLon, loc: dict[str, Any]) -> HourlyForecast:
    hourly = loc["hourly"]
    start = datetime.strptime(hourly["time"][0], STAMP).replace(tzinfo=UTC)
    return HourlyForecast(
        cell=cell,
        start_utc=start,
        wind=hourly["wind_speed_10m"],
        gust=hourly["wind_gusts_10m"],
        rain=hourly["rain"],
        showers=hourly["showers"],
        snow=hourly["snowfall"],
    )
