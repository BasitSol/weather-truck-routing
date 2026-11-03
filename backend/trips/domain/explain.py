"""Human sentences for the recommendation: why the winner won, what it costs, what to watch."""

from __future__ import annotations

from trips.domain.models import Level, Route
from trips.domain.ranking import CRITERIA, high_or_unknown, rank_key, severe_or_worse


def _mi(value: float) -> str:
    """Miles at the precision the ranking compares (0.1 mi): '25.2 mi', '20 mi'."""
    return f"{round(value, 1):,.1f}".removesuffix(".0") + " mi"


def _duration(minutes: float) -> str:
    h, m = divmod(round(minutes), 60)
    return f"{h} h {m} min" if h else f"{m} min"


def _avg(r: Route) -> str:
    return "n/a" if r.avg_risk is None else f"{r.avg_risk:.2f}"


def _nouns(ranked: list[Route]) -> dict[str, str]:
    """Names for the mile criteria, exact about what they count for these routes.

    "Severe-or-worse" only when some route has No-Travel miles in that count, "High-or-unknown"
    only when some route has miles without a forecast; otherwise the plain level name.
    """
    any_nt = any(r.miles["no_travel"] > 0 for r in ranked)
    any_unknown = any(r.miles["unknown"] > 0 for r in ranked)
    return {
        "severe_miles": "Severe-or-worse" if any_nt else "Severe",
        "high_miles": "High-or-unknown" if any_unknown else "High",
    }


def _value(r: Route, criterion: str) -> str:
    if criterion == "severe_miles":
        return _mi(severe_or_worse(r))
    if criterion == "high_miles":
        return _mi(high_or_unknown(r))
    return _avg(r)


def _tied_on(criteria: list[str], nouns: dict[str, str]) -> str:
    """['severe_miles', 'high_miles'] → 'Severe and High miles'; with avg risk, '… miles and average risk'."""
    words = [nouns[c] for c in criteria if c in nouns]
    if "avg_risk" in criteria:
        parts = [f"{w} miles" for w in words] + ["average risk"]
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    joined = words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
    return f"{joined} miles"


def _who_ties(ranked: list[Route], tied: list[Route]) -> str:
    """'All routes' when every other route tied with the winner, otherwise their names."""
    if len(tied) == len(ranked) - 1:
        return "All routes"
    return " and ".join(r.label for r in [ranked[0], *tied])


def explain(ranked: list[Route], decided_by: str) -> list[str]:
    """One sentence naming the criterion that separated the winner, plus the time trade-off.

    Only routes that genuinely tie with the winner on the earlier criteria are named as tied; a
    route that already lost on an earlier criterion is not part of that comparison.
    """
    best = ranked[0]
    if decided_by == "only_route":
        return [f"{best.label} is the only distinct truck route found for this trip."]
    if decided_by == "tie":
        return [f"All routes tie on every criterion, including travel time; {best.label} is listed first."]

    nouns = _nouns(ranked)
    k = CRITERIA.index(decided_by)
    tied = [r for r in ranked[1:] if rank_key(r)[:k] == rank_key(best)[:k]]
    prefix = f"{_who_ties(ranked, tied)} tie on {_tied_on(list(CRITERIA[:k]), nouns)}; " if k else ""
    others = ", ".join(f"{r.label}: {_value(r, decided_by)}" for r in tied)

    if decided_by in nouns:
        reason = (
            f"{prefix}{best.label} has the fewest {nouns[decided_by]} miles: "
            f"{_value(best, decided_by)} ({others})."
        )
    elif decided_by == "avg_risk":
        reason = f"{prefix}{best.label} has the lowest average risk: {_avg(best)} ({others})."
    else:  # duration
        which = "the fastest" if len(tied) == len(ranked) - 1 else "the faster of them"
        reason = f"{prefix}{best.label} is {which} ({_duration(best.duration_min)})."

    fastest = min(ranked, key=lambda r: r.duration_s)
    if best.duration_s <= fastest.duration_s:
        return [reason] if decided_by == "duration" else [reason, "It is also the fastest route."]
    extra_min = max(1, round(best.duration_min - fastest.duration_min))
    return [
        reason,
        f"+{_duration(extra_min)} vs the fastest route, {fastest.label}, "
        f"which has {_why_lost(fastest, best, nouns)}.",
    ]


def _why_lost(loser: Route, winner: Route, nouns: dict[str, str]) -> str:
    """The first ranking criterion on which `loser` is worse than `winner`, as a phrase."""
    for criterion, a, b in zip(CRITERIA, rank_key(loser), rank_key(winner), strict=True):
        if a == b:
            continue
        if criterion in nouns:
            return (
                f"more {nouns[criterion]} miles ({_value(loser, criterion)} vs {_value(winner, criterion)})"
            )
        return f"a higher average risk ({_avg(loser)} vs {_avg(winner)})"
    return "the same risk"  # unreachable: a faster route that ties on risk would have won


def warnings(ranked: list[Route], recommended: Route) -> list[str]:
    """No-Travel exposure first (strongest on the recommended route), then missing forecasts."""
    out: list[str] = []
    nt = recommended.miles["no_travel"]
    if nt > 0:
        out.append(
            f"Do not depart: the recommended route still crosses {_mi(nt)} of No-Travel conditions. "
            "Consider a later departure."
        )
    for r in ranked:
        if r is not recommended and r.miles["no_travel"] > 0:
            out.append(f"{r.label} crosses {_mi(r.miles['no_travel'])} of No-Travel conditions.")
    for r in ranked:
        unknown = sum(1 for cp in r.checkpoints if cp.risk == Level.UNKNOWN)
        if unknown:
            noun = "checkpoint" if unknown == 1 else "checkpoints"
            verb = "has" if unknown == 1 else "have"
            out.append(
                f"{unknown} {noun} on {r.label} {verb} no forecast data. "
                "They are shown as Unknown and counted as High when ranking."
            )
    return out
