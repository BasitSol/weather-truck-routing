"""Truck routing via Valhalla (keyless public instance by default; self-hostable).

One request with `costing=truck`, the truck's weight, and `alternates=2` returns up to three
routes. Valhalla reports time per maneuver, so cumulative time along the polyline is built by
spreading each maneuver's time over its stretch of shape in proportion to distance.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from trips.domain.geo import cumulative_miles
from trips.domain.models import Place, Route
from trips.providers.base import NoRouteError, ProviderError, client, request_json
from trips.providers.polyline import decode

log = logging.getLogger(__name__)

LB_TO_METRIC_TON = 0.00045359237
LABELS = ("Route A", "Route B", "Route C")


class ValhallaRouting:
    name = "valhalla"

    def __init__(
        self, url: str, user_agent: str | None = None, backoff_s: float = 0.4, api_key: str | None = None
    ) -> None:
        self.url = url
        self.user_agent = user_agent
        self.backoff_s = backoff_s
        self.api_key = api_key  # hosted Valhalla (e.g. Stadia Maps); the public demo server needs none

    async def routes(self, origin: Place, destination: Place, gross_lb: int) -> list[Route]:
        body = {
            "locations": [
                {"lat": origin.lat, "lon": origin.lon},
                {"lat": destination.lat, "lon": destination.lon},
            ],
            "costing": "truck",
            "costing_options": {"truck": {"weight": round(gross_lb * LB_TO_METRIC_TON, 2)}},
            "alternates": 2,
            "units": "miles",
            "directions_type": "maneuvers",
            # Hosted Valhalla (Stadia) omits maneuvers, and with them per-stretch times, without narrative.
            "narrative": True,
        }
        async with client(self.user_agent) as http:
            try:
                payload = await request_json(
                    http,
                    "POST",
                    self.url,
                    provider=self.name,
                    backoff_s=self.backoff_s,
                    params={"api_key": self.api_key} if self.api_key else None,
                    json=body,
                )
            except httpx.HTTPStatusError as exc:
                raise _client_error(exc.response) from exc

        trips = [payload["trip"]] + [alt["trip"] for alt in payload.get("alternates", [])]
        return [_parse_trip(trip, i) for i, trip in enumerate(trips[: len(LABELS)])]


class FallbackRouting:
    """Primary routing service first; the secondary covers outages and short-handed answers.

    - Primary down: ask the secondary instead.
    - Primary returned fewer than three routes: ask the secondary too and append its routes
      (analyze() drops duplicates and keeps three), because the brief asks for three options.
    - "No route" is an answer about the road network, not an outage, so it is never retried.
    """

    name = "valhalla"

    def __init__(self, primary: ValhallaRouting, secondary: ValhallaRouting) -> None:
        self.primary, self.secondary = primary, secondary

    async def routes(self, origin: Place, destination: Place, gross_lb: int) -> list[Route]:
        try:
            routes = await self.primary.routes(origin, destination, gross_lb)
        except ProviderError as exc:
            log.warning("primary routing failed (%s); trying the fallback server", exc.detail)
            return await self.secondary.routes(origin, destination, gross_lb)
        if len(routes) >= len(LABELS):
            return routes
        try:
            return routes + await self.secondary.routes(origin, destination, gross_lb)
        except (ProviderError, NoRouteError) as exc:
            log.info("no extra routes from the fallback server: %s", exc)
            return routes


def _client_error(response: httpx.Response) -> Exception:
    try:
        detail = response.json()
    except ValueError:
        detail = {}
    code = detail.get("error_code")
    if code == 154:  # path distance exceeds the server's limit
        return NoRouteError("This trip is longer than the routing service supports. Try a shorter trip.")
    if code in {442, 443, 170, 171}:  # no path, or a location can't reach a road open to trucks
        return NoRouteError("No truck route was found between these places.")
    return ProviderError(
        "valhalla", detail.get("error", f"HTTP {response.status_code}"), response.status_code
    )


def _parse_trip(trip: dict[str, Any], index: int) -> Route:
    points, cum_s = [], [0.0]
    for leg in trip["legs"]:
        leg_points = decode(leg["shape"])
        leg_cum = cumulative_miles(leg_points)
        leg_s = [0.0] * len(leg_points)
        # Per-maneuver times give speed changes along the leg; without them, assume constant speed.
        maneuvers = leg.get("maneuvers") or [
            {"begin_shape_index": 0, "end_shape_index": len(leg_points) - 1, "time": leg["summary"]["time"]}
        ]
        for m in maneuvers:
            a, b = m["begin_shape_index"], m["end_shape_index"]
            span_mi = leg_cum[b] - leg_cum[a]
            for i in range(a + 1, b + 1):
                share = (leg_cum[i] - leg_cum[a]) / span_mi if span_mi > 0 else 1.0
                leg_s[i] = leg_s[a] + share * m["time"]
        offset = cum_s[-1]
        skip = 1 if points else 0  # consecutive legs share their joining point
        points.extend(leg_points[skip:])
        cum_s.extend(offset + s for s in leg_s[skip:])
    cum_s = cum_s[1:]

    summary = trip["summary"]
    length_mi, duration_s = float(summary["length"]), float(summary["time"])
    raw_cum = cumulative_miles(points)
    scale = length_mi / raw_cum[-1] if raw_cum[-1] > 0 else 1.0  # agree exactly with the API's length
    time_scale = duration_s / cum_s[-1] if cum_s[-1] > 0 else 1.0

    notices = []
    if summary.get("has_ferry"):
        notices.append("Includes a ferry crossing.")
    if summary.get("has_time_restrictions"):
        notices.append("Uses roads with time-based restrictions.")

    return Route(
        id=f"r{index + 1}",
        label=LABELS[index],
        points=points,
        cum_mi=[c * scale for c in raw_cum],
        cum_s=[s * time_scale for s in cum_s],
        length_mi=length_mi,
        duration_s=duration_s,
        notices=notices,
    )
