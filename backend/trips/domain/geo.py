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
