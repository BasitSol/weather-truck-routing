"""Per-route aggregation: miles at each level, average risk, contiguous risk segments."""

from __future__ import annotations

from trips.domain.models import MILES_KEYS, Checkpoint, Level, Route, Segment


def miles_by_level(checkpoints: list[Checkpoint]) -> dict[str, float]:
    miles = dict.fromkeys(MILES_KEYS.values(), 0.0)
    for cp in checkpoints:
        miles[MILES_KEYS[cp.risk]] += cp.owned_mi
    return {k: round(v, 2) for k, v in miles.items()}


def avg_risk(checkpoints: list[Checkpoint]) -> float | None:
    """Average risk along the route (D10): each checkpoint's score weighted by the miles it covers.

    Miles with no forecast count as High (D13): a gap in the data must never make a route look
    safer than one whose weather is known.
    """
    total = sum(cp.owned_mi for cp in checkpoints)
    if total <= 0:
        return None
    weighted = sum(
        (Level.HIGH if cp.risk == Level.UNKNOWN else int(cp.risk)) * cp.owned_mi for cp in checkpoints
    )
    return round(weighted / total, 4)


def segments(checkpoints: list[Checkpoint]) -> list[Segment]:
    """Contiguous stretches of equal risk, using each checkpoint's owned miles."""
    out: list[Segment] = []
    start = 0.0
    for cp in checkpoints:
        end = start + cp.owned_mi
        if out and out[-1].risk == cp.risk:
            out[-1] = Segment(out[-1].from_mi, round(end, 3), cp.risk)
        else:
            out.append(Segment(round(start, 3), round(end, 3), cp.risk))
        start = end
    return out


def summarize(route: Route) -> None:
    """Fill a route's aggregates from its classified checkpoints."""
    route.miles = miles_by_level(route.checkpoints)
    route.avg_risk = avg_risk(route.checkpoints)
    route.segments = segments(route.checkpoints)
    known = [cp.risk for cp in route.checkpoints if cp.risk != Level.UNKNOWN]
    route.worst = max(known) if known else Level.UNKNOWN
