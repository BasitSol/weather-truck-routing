"""Caching decorators around providers. Same Protocols in, same Protocols out."""

from __future__ import annotations

import hashlib
from datetime import datetime

from django.core.cache import cache

from trips.domain.models import LatLon, Place, Route
from trips.domain.weather import HourlyForecast
from trips.providers.base import GeocodeProvider, RoutingProvider, WeatherProvider


class CachedRouting:
    def __init__(self, inner: RoutingProvider, ttl_s: int) -> None:
        self.inner, self.ttl_s, self.name = inner, ttl_s, inner.name

    async def routes(
        self, origin: Place, destination: Place, gross_lb: int, via: LatLon | None = None
    ) -> list[Route]:
        if via is not None:  # single detour requests are part of a cached trip answer, not cached alone
            return await self.inner.routes(origin, destination, gross_lb, via=via)
        raw = f"{origin.lat:.5f},{origin.lon:.5f}|{destination.lat:.5f},{destination.lon:.5f}|{gross_lb}"
        key = f"routes:{self.name}:{hashlib.sha1(raw.encode()).hexdigest()}"
        hit: list[Route] | None = cache.get(key)
        if hit is not None:
            return hit
        routes = await self.inner.routes(origin, destination, gross_lb)
        cache.set(key, routes, self.ttl_s)
        return routes


class CachedWeather:
    """Per-cell cache: neighbouring routes and repeat analyses share forecasts."""

    def __init__(self, inner: WeatherProvider, ttl_s: int) -> None:
        self.inner, self.ttl_s, self.name = inner, ttl_s, inner.name

    async def hourly(
        self, cells: list[LatLon], start_utc: datetime, end_utc: datetime
    ) -> dict[LatLon, HourlyForecast]:
        window = f"{start_utc:%Y%m%d%H}-{end_utc:%Y%m%d%H}"
        keys = {f"wx:{self.name}:{c.lat:.2f}:{c.lon:.2f}:{window}": c for c in cells}
        hits: dict[str, HourlyForecast] = cache.get_many(list(keys))
        out = {keys[k]: f for k, f in hits.items()}
        missing = [c for k, c in keys.items() if k not in hits]
        if missing:
            fresh = await self.inner.hourly(missing, start_utc, end_utc)
            cache.set_many(
                {f"wx:{self.name}:{c.lat:.2f}:{c.lon:.2f}:{window}": f for c, f in fresh.items()}, self.ttl_s
            )
            out.update(fresh)
        return out


class CachedGeocoder:
    def __init__(self, inner: GeocodeProvider, ttl_s: int) -> None:
        self.inner, self.ttl_s, self.name = inner, ttl_s, inner.name

    async def suggest(self, q: str, at: LatLon | None, limit: int) -> list[Place]:
        bias = f"{at.lat:.1f},{at.lon:.1f}" if at else "-"
        key = f"geo:{self.name}:{hashlib.sha1(f'{q.lower()}|{bias}|{limit}'.encode()).hexdigest()}"
        hit: list[Place] | None = cache.get(key)
        if hit is not None:
            return hit
        places = await self.inner.suggest(q, at, limit)
        if places:  # don't pin an upstream hiccup for a day
            cache.set(key, places, self.ttl_s)
        return places
