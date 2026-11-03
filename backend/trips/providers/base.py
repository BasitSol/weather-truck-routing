"""Ports for third-party services and the shared HTTP policy used by every adapter."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime
from typing import Any, Protocol

import httpx

from trips.domain.models import LatLon, Place, Route
from trips.domain.weather import HourlyForecast

TIMEOUT = httpx.Timeout(10.0, connect=4.0)
RETRY_STATUS = {429, 500, 502, 503, 504}


class ProviderError(Exception):
    """An upstream service failed after retries."""

    def __init__(self, provider: str, detail: str, status: int | None = None) -> None:
        super().__init__(f"{provider}: {detail}")
        self.provider = provider
        self.detail = detail
        self.status = status


class NoRouteError(Exception):
    """The routing service answered, but no truck route exists between the two places."""


class RoutingProvider(Protocol):
    name: str

    async def routes(self, origin: Place, destination: Place, gross_lb: int) -> list[Route]: ...


class WeatherProvider(Protocol):
    name: str

    async def hourly(
        self, cells: list[LatLon], start_utc: datetime, end_utc: datetime
    ) -> dict[LatLon, HourlyForecast]:
        """Forecasts for the cells it could fetch. Cells that failed are absent, never faked."""
        ...


class GeocodeProvider(Protocol):
    name: str

    async def suggest(self, q: str, at: LatLon | None, limit: int) -> list[Place]: ...


def client(user_agent: str | None = None) -> httpx.AsyncClient:
    headers = {"User-Agent": user_agent} if user_agent else {}
    return httpx.AsyncClient(timeout=TIMEOUT, headers=headers)


async def request_json(
    http: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    provider: str,
    retries: int = 2,
    backoff_s: float = 0.4,
    **kwargs: Any,
) -> Any:
    """JSON from `url`, retrying timeouts, 429 and 5xx with jittered exponential backoff.

    4xx responses other than 429 are returned to the caller via `httpx.HTTPStatusError` so the
    adapter can interpret them (e.g. Valhalla's "no path" 400).
    """
    for attempt in range(retries + 1):
        try:
            response = await http.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            if attempt == retries:
                raise ProviderError(provider, f"unreachable ({type(exc).__name__})") from exc
        else:
            if response.status_code not in RETRY_STATUS:
                response.raise_for_status()
                return response.json()
            if attempt == retries:
                raise ProviderError(provider, f"HTTP {response.status_code}", response.status_code)
        await asyncio.sleep(backoff_s * (2**attempt) * (0.5 + random.random()))
    raise AssertionError("unreachable")
