"""Which provider implementations the app uses. Tests swap them with `override(...)`."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from django.conf import settings

from trips.providers.base import GeocodeProvider, RoutingProvider, WeatherProvider
from trips.providers.open_meteo import OpenMeteoWeather
from trips.providers.photon import PhotonGeocoder
from trips.providers.valhalla import FallbackRouting, ValhallaRouting
from trips.services.cache import CachedGeocoder, CachedRouting, CachedWeather

_overrides: dict[str, Any] = {}


def routing() -> RoutingProvider:
    if "routing" in _overrides:
        return _overrides["routing"]
    public = ValhallaRouting(settings.VALHALLA_URL, settings.HTTP_USER_AGENT)
    inner: RoutingProvider = public
    if settings.STADIA_API_KEY:
        stadia = ValhallaRouting(
            settings.STADIA_ROUTE_URL, settings.HTTP_USER_AGENT, api_key=settings.STADIA_API_KEY
        )
        inner = FallbackRouting(stadia, public)
    return CachedRouting(inner, settings.CACHE_TTL_ROUTES)


def routing_service() -> str:
    """Which routing service is configured, for /health (never the key itself)."""
    return "stadia-maps (public valhalla fallback)" if settings.STADIA_API_KEY else "public valhalla"


def weather() -> WeatherProvider:
    return _overrides.get("weather") or CachedWeather(
        OpenMeteoWeather(settings.OPEN_METEO_URL, settings.HTTP_USER_AGENT), settings.CACHE_TTL_WEATHER
    )


def geocoder() -> GeocodeProvider:
    return _overrides.get("geocoder") or CachedGeocoder(
        PhotonGeocoder(settings.PHOTON_URL, settings.HTTP_USER_AGENT), settings.CACHE_TTL_GEOCODE
    )


@contextmanager
def override(**providers: Any) -> Iterator[None]:
    previous = dict(_overrides)
    _overrides.update(providers)
    try:
        yield
    finally:
        _overrides.clear()
        _overrides.update(previous)
