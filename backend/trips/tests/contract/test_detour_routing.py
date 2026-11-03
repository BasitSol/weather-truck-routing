"""Extra route options through detour waypoints when the routing service offers fewer than three."""

from __future__ import annotations

import pytest

from trips.domain.geo import cumulative_miles
from trips.domain.models import LatLon, Place, Route
from trips.providers.base import NoRouteError, ProviderError
from trips.services.alternatives import DetourRouting

DALLAS = Place("Dallas, TX", 32.7767, -96.7970)
HOUSTON = Place("Houston, TX", 29.7604, -95.3698)


def _route(points: list[LatLon], minutes_per_mile: float = 1.0) -> Route:
    cum = cumulative_miles(points)
    return Route(
        "r1",
        "Route A",
        points,
        cum,
        [m * 60 * minutes_per_mile for m in cum],
        cum[-1],
        cum[-1] * 60 * minutes_per_mile,
    )


def _via_path(a: Place, via: LatLon, b: Place, steps: int = 20) -> list[LatLon]:
    """A two-leg straight path through `via`, standing in for a road through the waypoint."""
    first = [
        LatLon(a.lat + (via.lat - a.lat) * i / steps, a.lon + (via.lon - a.lon) * i / steps)
        for i in range(steps)
    ]
    second = [
        LatLon(via.lat + (b.lat - via.lat) * i / steps, via.lon + (b.lon - via.lon) * i / steps)
        for i in range(steps + 1)
    ]
    return first + second


DIRECT = _route(
    _via_path(DALLAS, LatLon((DALLAS.lat + HOUSTON.lat) / 2, (DALLAS.lon + HOUSTON.lon) / 2), HOUSTON)
)


class Recorder:
    """A routing provider whose answers are scripted per call, recording every via it was asked for."""

    name = "fake"

    def __init__(self, base: list[Route], via_answer=None) -> None:  # type: ignore[no-untyped-def]
        self.base, self.via_answer, self.vias = base, via_answer, []

    async def routes(
        self, origin: Place, destination: Place, gross_lb: int, via: LatLon | None = None
    ) -> list[Route]:
        if via is None:
            return list(self.base)
        self.vias.append(via)
        answer = (
            self.via_answer(origin, destination, via)
            if self.via_answer
            else _route(_via_path(origin, via, destination))
        )
        if isinstance(answer, Exception):
            raise answer
        return [answer]


async def test_three_routes_from_the_service_need_no_detours() -> None:
    base = [
        DIRECT,
        _route(_via_path(DALLAS, LatLon(31.5, -95.2), HOUSTON)),
        _route(_via_path(DALLAS, LatLon(31.0, -97.0), HOUSTON)),
    ]
    inner = Recorder(base)

    routes = await DetourRouting(inner).routes(DALLAS, HOUSTON, 40_000)

    assert routes == base
    assert inner.vias == []


async def test_one_route_is_topped_up_with_a_detour_either_side() -> None:
    inner = Recorder([DIRECT])

    routes = await DetourRouting(inner).routes(DALLAS, HOUSTON, 40_000)

    assert len(routes) == 3
    assert len(inner.vias) == 2  # the first ring of detours was enough
    added = routes[1:]
    assert all(any("detour" in n for n in r.notices) for r in added)
    sides = {
        n.split("through a waypoint ")[1].split(" of")[0] for r in added for n in r.notices if "waypoint" in n
    }
    assert sides == {"west", "east"}


async def test_a_detour_much_slower_than_the_fastest_route_is_rejected() -> None:
    inner = Recorder(
        [DIRECT], via_answer=lambda o, d, via: _route(_via_path(o, via, d), minutes_per_mile=3.0)
    )

    routes = await DetourRouting(inner).routes(DALLAS, HOUSTON, 40_000)

    assert routes == [DIRECT]  # nothing within 50% of the fastest time; the API's warning will say so


async def test_a_detour_that_is_the_same_road_as_an_existing_route_is_dropped() -> None:
    inner = Recorder([DIRECT], via_answer=lambda o, d, via: _route(DIRECT.points))

    routes = await DetourRouting(inner).routes(DALLAS, HOUSTON, 40_000)

    assert routes == [DIRECT]


async def test_an_out_and_back_spur_to_the_waypoint_is_rejected() -> None:
    def spur(o: Place, d: Place, via: LatLon) -> Route:
        out = _via_path(o, via, o, steps=10)  # drive to the waypoint and straight back
        # Fast enough and a different length, so only the doubling-back check can reject it.
        return _route(out + DIRECT.points[1:], minutes_per_mile=0.5)

    inner = Recorder([DIRECT], via_answer=spur)

    assert await DetourRouting(inner).routes(DALLAS, HOUSTON, 40_000) == [DIRECT]


@pytest.mark.parametrize(
    "error", [NoRouteError("no road near the waypoint"), ProviderError("valhalla", "timeout", 504)]
)
async def test_a_failed_detour_request_is_skipped_never_fatal(error: Exception) -> None:
    calls: list[LatLon] = []

    def flaky(o: Place, d: Place, via: LatLon) -> Route | Exception:
        calls.append(via)
        return error if len(calls) == 1 else _route(_via_path(o, via, d))

    inner = Recorder([DIRECT], via_answer=flaky)

    routes = await DetourRouting(inner).routes(DALLAS, HOUSTON, 40_000)

    assert len(routes) == 3  # one side failed in the first ring; the wider ring filled the gap
    assert len(calls) == 4


async def test_detours_never_replace_the_services_own_routes_or_exceed_three() -> None:
    second = _route(_via_path(DALLAS, LatLon(31.5, -95.2), HOUSTON))
    inner = Recorder([DIRECT, second])

    routes = await DetourRouting(inner).routes(DALLAS, HOUSTON, 40_000)

    assert routes[:2] == [DIRECT, second]
    assert len(routes) == 3


async def test_a_via_request_passes_straight_through() -> None:
    inner = Recorder([DIRECT])
    via = LatLon(31.0, -96.0)

    routes = await DetourRouting(inner).routes(DALLAS, HOUSTON, 40_000, via=via)

    assert len(routes) == 1
    assert inner.vias == [via]
