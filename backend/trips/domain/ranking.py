"""Route recommendation: the brief's preference order, applied literally (D11).

1. Fewest Severe miles. No-Travel miles count here too: No Travel is worse than Severe.
2. Fewest High miles. Miles with no forecast count here too, so missing data is never a free pass.
3. Lowest average risk (distance-weighted, see miles.avg_risk).
4. Shortest travel time

Miles are compared at 0.1 mi and average risk at 2 dp, the precision the UI and the explanation
show, so the deciding criterion is always one a reader can see.
"""

from __future__ import annotations

import math

from trips.domain.models import Route

CRITERIA = ("severe_miles", "high_miles", "avg_risk", "duration")


def severe_or_worse(route: Route) -> float:
    return route.miles["severe"] + route.miles["no_travel"]


def high_or_unknown(route: Route) -> float:
    return route.miles["high"] + route.miles["unknown"]


def rank_key(route: Route) -> tuple[float, float, float, float]:
    return (
        round(severe_or_worse(route), 1),
        round(high_or_unknown(route), 1),
        math.inf if route.avg_risk is None else round(route.avg_risk, 2),
        route.duration_s,
    )


def rank(routes: list[Route]) -> tuple[list[Route], str]:
    """Routes best-first, and the criterion that separated the winner from the runner-up."""
    ranked = sorted(routes, key=rank_key)  # stable: equal routes keep the API's order
    if len(ranked) < 2:
        return ranked, "only_route"
    best, runner_up = rank_key(ranked[0]), rank_key(ranked[1])
    for name, a, b in zip(CRITERIA, best, runner_up, strict=True):
        if a != b:
            return ranked, name
    return ranked, "tie"
