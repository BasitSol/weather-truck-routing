"""Distances and positions along a polyline."""

from __future__ import annotations

import itertools
import math
from bisect import bisect_right

from trips.domain.models import LatLon, Route

EARTH_RADIUS_MI = 3958.7613
GRID_DEG = 0.05  # weather grid (~3.5 mi); neighbouring routes share cells (SPEC §3.4)


def haversine_mi(a: LatLon, b: LatLon) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(points: list[LatLon]) -> list[float]:
    cum = [0.0]
    for prev, cur in itertools.pairwise(points):
        cum.append(cum[-1] + haversine_mi(prev, cur))
    return cum


def interpolate(xs: list[float], ys: list[float], x: float) -> float:
    """Piecewise-linear y(x) over ascending xs, clamped to the ends."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect_right(xs, x) - 1
    span = xs[i + 1] - xs[i]
    t = 0.0 if span == 0 else (x - xs[i]) / span
    return ys[i] + t * (ys[i + 1] - ys[i])


def point_at_mile(points: list[LatLon], cum_mi: list[float], mile: float) -> LatLon:
    lat = interpolate(cum_mi, [p.lat for p in points], mile)
    lon = interpolate(cum_mi, [p.lon for p in points], mile)
    return LatLon(round(lat, 6), round(lon, 6))


def snap(p: LatLon, step: float = GRID_DEG) -> LatLon:
    """Round a point to the weather grid so nearby samples share one forecast request."""
    return LatLon(round(round(p.lat / step) * step, 4), round(round(p.lon / step) * step, 4))


def slice_line(points: list[LatLon], cum_mi: list[float], from_mi: float, to_mi: float) -> list[LatLon]:
    """The part of a polyline between two mile marks, with interpolated end points."""
    inner = [p for p, m in zip(points, cum_mi, strict=True) if from_mi < m < to_mi]
    return [point_at_mile(points, cum_mi, from_mi), *inner, point_at_mile(points, cum_mi, to_mi)]


def simplify(points: list[LatLon], tolerance_deg: float = 0.0002) -> list[LatLon]:
    """Ramer–Douglas–Peucker (planar, in degrees). ~20 m tolerance keeps the drawn shape exact."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        a, b = points[first], points[last]
        dx, dy = b.lon - a.lon, b.lat - a.lat
        norm = math.hypot(dx, dy)
        worst, worst_i = 0.0, -1
        for i in range(first + 1, last):
            p = points[i]
            if norm == 0:
                d = math.hypot(p.lon - a.lon, p.lat - a.lat)
            else:
                d = abs(dy * (p.lon - a.lon) - dx * (p.lat - a.lat)) / norm
            if d > worst:
                worst, worst_i = d, i
        if worst > tolerance_deg:
            keep[worst_i] = True
            stack += [(first, worst_i), (worst_i, last)]
    return [p for p, k in zip(points, keep, strict=True) if k]


def distinct_routes(
    routes: list[Route], length_tol: float = 0.02, midpoint_tol_mi: float = 2.0
) -> list[Route]:
    """Drop alternatives that are effectively the same road as an earlier route (D15)."""
    kept: list[Route] = []
    for r in routes:
        mid = point_at_mile(r.points, r.cum_mi, r.length_mi / 2)
        same = any(
            abs(r.length_mi - k.length_mi) <= length_tol * k.length_mi
            and haversine_mi(mid, point_at_mile(k.points, k.cum_mi, k.length_mi / 2)) <= midpoint_tol_mi
            for k in kept
        )
        if not same:
            kept.append(r)
    return kept


# --- Detour waypoints, for extra route options when the routing service offers too few (D15) ---

MILES_PER_DEG_LAT = EARTH_RADIUS_MI * math.pi / 180


def _plane(a: LatLon, b: LatLon) -> tuple[LatLon, float, float, float]:
    """Midpoint of a→b and the a→b vector in miles (east, north) on a local flat plane."""
    mid = LatLon((a.lat + b.lat) / 2, (a.lon + b.lon) / 2)
    kx = math.cos(math.radians(mid.lat)) * MILES_PER_DEG_LAT
    east, north = (b.lon - a.lon) * kx, (b.lat - a.lat) * MILES_PER_DEG_LAT
    return mid, kx, east, north


def detour_points(a: LatLon, b: LatLon, fraction: float) -> tuple[LatLon, LatLon]:
    """Two waypoints off the midpoint of a→b, one each side of the direct line, `fraction` of the
    trip's straight-line length away. A route forced through one follows a different corridor."""
    mid, kx, east, north = _plane(a, b)
    length = math.hypot(east, north)
    if length == 0:
        return mid, mid
    offset = fraction * haversine_mi(a, b)
    perp_east, perp_north = -north / length * offset, east / length * offset  # left of travel
    left = LatLon(round(mid.lat + perp_north / MILES_PER_DEG_LAT, 6), round(mid.lon + perp_east / kx, 6))
    right = LatLon(round(mid.lat - perp_north / MILES_PER_DEG_LAT, 6), round(mid.lon - perp_east / kx, 6))
    return left, right


def side_of_line(a: LatLon, b: LatLon, p: LatLon) -> str:
    """Compass side of the direct a→b line that `p` lies on: "north", "south", "east" or "west"."""
    mid, kx, _, _ = _plane(a, b)
    east, north = (p.lon - mid.lon) * kx, (p.lat - mid.lat) * MILES_PER_DEG_LAT
    if abs(north) >= abs(east):
        return "north" if north >= 0 else "south"
    return "east" if east >= 0 else "west"


def doubles_back(
    route: Route, near_mi: float = 0.6, min_gap_mi: float = 15.0, min_overlap_mi: float = 5.0
) -> bool:
    """Whether a route drives back along road it already used: a later stretch, at least
    `min_gap_mi` further on, running within `near_mi` of an earlier one for `min_overlap_mi` or more.
    That is the out-and-back spur a waypoint can force, not a real alternative."""
    step = max(1.0, route.length_mi / 400)  # at most ~400 samples, so this stays cheap
    miles = [i * step for i in range(int(route.length_mi / step) + 1)]
    samples = [point_at_mile(route.points, route.cum_mi, m) for m in miles]
    overlap = 0.0
    for i, (mi, p) in enumerate(zip(miles, samples, strict=True)):
        later = (q for mj, q in zip(miles[i + 1 :], samples[i + 1 :], strict=True) if mj - mi >= min_gap_mi)
        if any(haversine_mi(p, q) <= near_mi for q in later):
            overlap += step
            if overlap >= min_overlap_mi:
                return True
    return False
