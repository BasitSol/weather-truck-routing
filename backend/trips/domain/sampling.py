"""Where checkpoints go along a route, and which stretch of road each one speaks for."""

from __future__ import annotations

import itertools

INTERVALS = (10, 25, 50)  # the brief's three sampling options, in miles (D1)


def checkpoint_miles(length_mi: float, interval: float) -> list[float]:
    """Miles 0, N, 2N, … plus the destination.

    A regular point closer than N/4 to the destination is dropped, so the last stretch isn't
    sampled twice a few miles apart.
    """
    miles: list[float] = [0.0]
    m = float(interval)
    while m < length_mi:
        miles.append(m)
        m += interval
    if len(miles) > 1 and length_mi - miles[-1] < interval / 4:
        miles.pop()
    miles.append(round(length_mi, 3))
    return miles


def owned_miles(miles: list[float], length_mi: float) -> list[float]:
    """Midpoint ownership (D9): each checkpoint owns half-way to each neighbour.

    The result sums to the route length, so miles-per-level never double counts.
    """
    bounds = [0.0] + [(a + b) / 2 for a, b in itertools.pairwise(miles)] + [length_mi]
    return [hi - lo for lo, hi in itertools.pairwise(bounds)]
