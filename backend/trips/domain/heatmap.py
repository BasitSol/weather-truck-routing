"""Corridor heat: risk at points along every route for each hour 0–48 after departure (SPEC §5)."""

from __future__ import annotations

from datetime import datetime, timedelta

from trips.domain.geo import point_at_mile, snap
from trips.domain.models import LatLon, Level, Route
from trips.domain.risk import checkpoint_risk
from trips.domain.weather import HourlyForecast

HEAT_HOURS = 48  # slider range; series hold HEAT_HOURS + 1 values (hour 0 … hour 48 inclusive)


def corridor_points(routes: list[Route], spacing_mi: float = 10, cap: int = 150) -> list[LatLon]:
    """Grid-snapped points every `spacing_mi` along each route, merged across routes.

    `cap` is shared by all routes, so long trips with several routes stay within the weather
    service's free request budget; the spacing widens instead.
    """
    seen: dict[LatLon, None] = {}
    total_mi = sum(r.length_mi for r in routes)
    spacing = max(spacing_mi, total_mi / max(cap - 1, 1))
    for route in routes:
        n = int(route.length_mi // spacing)
        for i in range(n + 1):
            seen.setdefault(snap(point_at_mile(route.points, route.cum_mi, i * spacing)), None)
        seen.setdefault(snap(route.points[-1]), None)
    return list(seen)


def heat_series(forecast: HourlyForecast | None, start_utc: datetime, load_lb: int) -> list[int]:
    """Risk level for hours 0…48 after `start_utc` — same classifier and load rules as checkpoints."""
    if forecast is None:
        return [int(Level.UNKNOWN)] * (HEAT_HOURS + 1)
    return [
        int(checkpoint_risk(forecast.weather_at(start_utc + timedelta(hours=h)), load_lb).level)
        for h in range(HEAT_HOURS + 1)
    ]
