"""Extra route options when the routing service offers fewer than three (D15).

The brief asks for three route options. Valhalla returns alternates only where it finds them, and
on corridors one interstate dominates (Dallas to Houston) it returns none. Then the same routing
service is asked again with one "through" waypoint to the side of the direct line, first near it,
then further out. The service still plans every road; a candidate is kept only if it is a
different road from the routes already kept, no more than MAX_SLOWDOWN slower than the fastest,
and does not drive out to the waypoint and back. Requests that fail are skipped, never fatal; if
nothing qualifies, the trip shows the routes that exist and the API says so.
"""

from __future__ import annotations

import asyncio
import logging

from trips.domain.geo import detour_points, distinct_routes, doubles_back, side_of_line
from trips.domain.models import LatLon, Place, Route
from trips.providers.base import NoRouteError, ProviderError, RoutingProvider

log = logging.getLogger(__name__)

TARGET = 3
RINGS = (0.12, 0.25)  # waypoint offset from the midpoint, as a share of the straight-line trip
MAX_SLOWDOWN = 1.5  # a detour may take at most 50% longer than the fastest route


class DetourRouting:
    def __init__(self, inner: RoutingProvider) -> None:
        self.inner, self.name = inner, inner.name

    async def routes(
        self, origin: Place, destination: Place, gross_lb: int, via: LatLon | None = None
    ) -> list[Route]:
        if via is not None:
            return await self.inner.routes(origin, destination, gross_lb, via=via)

        kept = distinct_routes(await self.inner.routes(origin, destination, gross_lb))
        if len(kept) >= TARGET or not kept:
            return kept[:TARGET]
        fastest = min(r.duration_s for r in kept)

        for fraction in RINGS:
            if len(kept) >= TARGET:
                break
            vias = detour_points(origin.pos, destination.pos, fraction)
            found = await asyncio.gather(*(self._through(origin, destination, gross_lb, v) for v in vias))
            for waypoint, route in zip(vias, found, strict=True):
                if route is None or len(kept) >= TARGET:
                    continue
                if route.duration_s > MAX_SLOWDOWN * fastest or doubles_back(route):
                    continue
                if len(distinct_routes([*kept, route])) == len(kept):  # same road as one already kept
                    continue
                side = side_of_line(origin.pos, destination.pos, waypoint)
                route.notices = [
                    *route.notices,
                    f"Added as a detour alternative: routed through a waypoint {side} of the direct line, "
                    "because the routing service offered fewer than three routes.",
                ]
                kept.append(route)
        return kept

    async def _through(self, origin: Place, destination: Place, gross_lb: int, via: LatLon) -> Route | None:
        try:
            found = await self.inner.routes(origin, destination, gross_lb, via=via)
        except (NoRouteError, ProviderError) as exc:  # e.g. no truck road near the waypoint
            log.info("detour through %s skipped: %s", via, exc)
            return None
        return found[0] if found else None
