"""One trip analysis, end to end (docs/ARCHITECTURE.md §3).

routes → distinct routes → checkpoints with ETAs → weather for every grid cell at once →
classify at ETA → aggregate → rank and explain → corridor heat for hours 0–48.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from trips.domain.eta import eta, time_at_mile
from trips.domain.explain import explain, warnings
from trips.domain.geo import distinct_routes, point_at_mile, snap
from trips.domain.heatmap import HEAT_HOURS, corridor_points, heat_series
from trips.domain.miles import summarize
from trips.domain.models import Checkpoint, HeatPoint, LatLon, Place, Recommendation, Route
from trips.domain.ranking import rank
from trips.domain.risk import checkpoint_risk
from trips.domain.sampling import checkpoint_miles, owned_miles
from trips.domain.weather import HourlyForecast
from trips.providers.base import RoutingProvider, WeatherProvider
from trips.providers.valhalla import LABELS
from trips.services.timezones import tz_at

log = logging.getLogger(__name__)

FORECAST_HORIZON = timedelta(days=15)  # Open-Meteo serves 16 days from today; stay inside it


class WeatherUnavailable(Exception):
    """Every weather request failed — there is nothing honest to show."""


@dataclass(frozen=True)
class TripRequest:
    origin: Place
    destination: Place
    departure_utc: datetime
    load_lb: int
    interval: int


@dataclass
class Analysis:
    request: TripRequest
    routes: list[Route]
    recommendation: Recommendation
    heat: list[HeatPoint]
    timings_ms: dict[str, int] = field(default_factory=dict)
    providers: dict[str, str] = field(default_factory=dict)


async def analyze(req: TripRequest, routing: RoutingProvider, weather: WeatherProvider) -> Analysis:
    t0 = time.perf_counter()
    routes = distinct_routes(await routing.routes(req.origin, req.destination, req.load_lb))
    for i, r in enumerate(routes):  # relabel after dedupe so labels stay A, B, C
        r.id, r.label = f"r{i + 1}", LABELS[i]
    t_route = time.perf_counter()

    for r in routes:
        r.checkpoints = _checkpoints(r, req)
    heat_cells = corridor_points(routes)
    cells = list(dict.fromkeys([snap(cp.pos) for r in routes for cp in r.checkpoints] + heat_cells))

    start, end = _forecast_window(req.departure_utc, routes)
    forecasts = await weather.hourly(cells, start, end) if end > start else {}
    if not forecasts:
        raise WeatherUnavailable("No forecast could be fetched for this trip.")
    t_weather = time.perf_counter()

    for r in routes:
        _classify(r, forecasts, req.load_lb)
        summarize(r)
    ranked, decided_by = rank(routes)
    notes = warnings(ranked, recommended=ranked[0])
    if len(routes) < len(LABELS):
        notes.append(
            f"Only {len(routes)} distinct truck route{'s' if len(routes) != 1 else ''} "
            "could be found for this trip."
        )
    recommendation = Recommendation(
        route_id=ranked[0].id,
        ranking=[r.id for r in ranked],
        decided_by=decided_by,
        reasons=explain(ranked, decided_by),
        warnings=notes,
    )
    heat = [HeatPoint(c, heat_series(forecasts.get(c), req.departure_utc, req.load_lb)) for c in heat_cells]
    t_done = time.perf_counter()

    timings = {
        "route": round((t_route - t0) * 1000),
        "weather": round((t_weather - t_route) * 1000),
        "compute": round((t_done - t_weather) * 1000),
        "total": round((t_done - t0) * 1000),
    }
    log.info(
        "analyze routes=%d cells=%d fetched=%d timings=%s", len(routes), len(cells), len(forecasts), timings
    )
    return Analysis(
        request=req,
        routes=routes,  # API order (Route A, B, C); ranking order is in the recommendation
        recommendation=recommendation,
        heat=heat,
        timings_ms=timings,
        providers={"routing": routing.name, "weather": weather.name},
    )


def _checkpoints(route: Route, req: TripRequest) -> list[Checkpoint]:
    miles = checkpoint_miles(route.length_mi, req.interval)
    owned = owned_miles(miles, route.length_mi)
    out = []
    for m, own in zip(miles, owned, strict=True):
        pos = point_at_mile(route.points, route.cum_mi, m)
        seconds = time_at_mile(route.cum_mi, route.cum_s, m)
        out.append(
            Checkpoint(mile=m, pos=pos, eta_utc=eta(req.departure_utc, seconds), owned_mi=own, tz=tz_at(pos))
        )
    return out


def _classify(route: Route, forecasts: dict[LatLon, HourlyForecast], load_lb: int) -> None:
    for cp in route.checkpoints:
        forecast = forecasts.get(snap(cp.pos))
        cp.weather = forecast.weather_at(cp.eta_utc) if forecast else None
        result = checkpoint_risk(cp.weather, load_lb)
        cp.risk, cp.levels, cp.driver = result.level, result.levels, result.driver


def _forecast_window(departure_utc: datetime, routes: list[Route]) -> tuple[datetime, datetime]:
    """Hourly stamps covering departure … max(last ETA, departure + 48 h), plus the closing bucket."""
    last_eta = max(cp.eta_utc for r in routes for cp in r.checkpoints)
    start = departure_utc.replace(minute=0, second=0, microsecond=0)
    until = max(last_eta, departure_utc + timedelta(hours=HEAT_HOURS))
    end = until.replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)
    horizon = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + FORECAST_HORIZON
    return start, min(end, horizon)
