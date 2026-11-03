"""Aggregation per route, the brief's literal ranking order, and the explanation sentence."""

from datetime import UTC, datetime

import pytest

from trips.domain.explain import explain, warnings
from trips.domain.miles import avg_risk, miles_by_level, segments, summarize
from trips.domain.models import Checkpoint, LatLon, Level, Route
from trips.domain.ranking import rank

T = datetime(2026, 11, 3, tzinfo=UTC)


def cp(mile: float, owned: float, risk: Level) -> Checkpoint:
    return Checkpoint(mile=mile, pos=LatLon(0, 0), eta_utc=T, owned_mi=owned, risk=risk)


def route(rid: str, label: str, minutes: float, risks: list[Level], interval: float = 10) -> Route:
    """A straight synthetic route whose checkpoints are `interval` miles apart."""
    length = interval * (len(risks) - 1)
    owned = [interval / 2] + [interval] * (len(risks) - 2) + [interval / 2]
    r = Route(
        id=rid,
        label=label,
        points=[],
        cum_mi=[],
        cum_s=[],
        length_mi=length,
        duration_s=minutes * 60,
    )
    r.checkpoints = [cp(i * interval, owned[i], lvl) for i, lvl in enumerate(risks)]
    summarize(r)
    return r


L, M, H, S, NT, U = Level.LOW, Level.MODERATE, Level.HIGH, Level.SEVERE, Level.NO_TRAVEL, Level.UNKNOWN


# ---------------------------------------------------------------- aggregation


def test_miles_by_level_sum_to_route_length() -> None:
    cps = [cp(0, 5, L), cp(10, 10, H), cp(20, 10, H), cp(30, 5, U)]

    miles = miles_by_level(cps)

    assert miles == {"low": 5, "moderate": 0, "high": 20, "severe": 0, "no_travel": 0, "unknown": 5}


def test_average_risk_is_weighted_by_the_miles_each_checkpoint_covers() -> None:
    # A Severe end checkpoint covers 5 mi of 30: plain mean would say 0.75, the route average is 0.5.
    cps = [cp(0, 5, S), cp(10, 10, L), cp(20, 10, L), cp(30, 5, L)]

    assert avg_risk(cps) == pytest.approx(0.5)


def test_miles_without_a_forecast_count_as_high_in_the_average() -> None:
    cps = [cp(0, 5, L), cp(10, 10, H), cp(20, 5, U)]

    assert avg_risk(cps) == pytest.approx((0 * 5 + 2 * 10 + 2 * 5) / 20)


def test_segments_are_contiguous_and_merge_equal_neighbours() -> None:
    cps = [cp(0, 5, L), cp(10, 10, L), cp(20, 10, S), cp(30, 5, L)]

    segs = segments(cps)

    assert [(s.from_mi, s.to_mi, s.risk) for s in segs] == [(0, 15, L), (15, 25, S), (25, 30, L)]


def test_summary_sets_worst_known_level() -> None:
    r = route("r1", "Route A", 60, [L, H, U])

    assert r.worst == H


# ---------------------------------------------------------------- ranking (the brief's order)


def test_fewest_severe_miles_wins_even_when_slower() -> None:
    a = route("r1", "Route A", 300, [L, S, S, L])
    b = route("r2", "Route B", 360, [L, H, H, L])
    c = route("r3", "Route C", 330, [L, S, L, L])

    ranked, decided_by = rank([a, b, c])

    assert [r.id for r in ranked] == ["r2", "r3", "r1"]
    assert decided_by == "severe_miles"


def test_no_travel_miles_count_inside_severe_miles() -> None:
    # No Travel is worse than Severe, so 20 No-Travel miles weigh more than 10 Severe miles.
    a = route("r1", "Route A", 300, [L, NT, NT, L])
    b = route("r2", "Route B", 360, [L, S, L, L])

    ranked, decided_by = rank([a, b])

    assert ranked[0].id == "r2"
    assert decided_by == "severe_miles"


def test_severe_or_worse_miles_decide_literally_even_against_no_travel() -> None:
    a = route("r1", "Route A", 300, [L, NT, L])  # 10 mi No Travel
    b = route("r2", "Route B", 360, [L, S, S])  # 15 mi Severe

    ranked, _ = rank([a, b])

    assert ranked[0].id == "r1"


def test_high_miles_break_a_severe_tie() -> None:
    a = route("r1", "Route A", 300, [L, H, H, L])
    b = route("r2", "Route B", 360, [L, H, L, L])

    ranked, decided_by = rank([a, b])

    assert ranked[0].id == "r2"
    assert decided_by == "high_miles"


def test_miles_without_a_forecast_count_as_high_when_ranking() -> None:
    a = route("r1", "Route A", 300, [L, H, L])  # 10 mi High
    b = route("r2", "Route B", 200, [L, U, U, L])  # 20 mi with no forecast: not a free pass

    ranked, decided_by = rank([a, b])

    assert ranked[0].id == "r1"
    assert decided_by == "high_miles"


def test_average_risk_breaks_a_high_miles_tie() -> None:
    a = route("r1", "Route A", 300, [M, M, L])
    b = route("r2", "Route B", 360, [L, M, L])

    ranked, decided_by = rank([a, b])

    assert ranked[0].id == "r2"
    assert decided_by == "avg_risk"


def test_travel_time_breaks_a_full_risk_tie() -> None:
    a = route("r1", "Route A", 360, [L, L, L])
    b = route("r2", "Route B", 300, [L, L, L])

    ranked, decided_by = rank([a, b])

    assert ranked[0].id == "r2"
    assert decided_by == "duration"


def test_a_single_route_is_recommended_by_default() -> None:
    ranked, decided_by = rank([route("r1", "Route A", 300, [L, L])])

    assert [r.id for r in ranked] == ["r1"]
    assert decided_by == "only_route"


# ---------------------------------------------------------------- explanation


def test_explanation_names_the_deciding_criterion_and_the_time_cost() -> None:
    a = route("r1", "Route A", 300, [L, S, S, L])
    b = route("r2", "Route B", 324, [L, H, H, L])
    c = route("r3", "Route C", 330, [L, S, L, L])
    ranked, decided_by = rank([a, b, c])

    reasons = explain(ranked, decided_by)

    assert reasons == [
        "Route B has the fewest Severe miles: 0 mi (Route C: 10 mi, Route A: 20 mi).",
        "+24 min vs the fastest route, Route A, which has more Severe miles (20 mi vs 0 mi).",
    ]


def test_explanation_says_severe_or_worse_when_no_travel_is_counted() -> None:
    a = route("r1", "Route A", 300, [L, NT, L])
    b = route("r2", "Route B", 360, [L, S, S])
    ranked, decided_by = rank([a, b])

    assert explain(ranked, decided_by)[0] == (
        "Route A has the fewest Severe-or-worse miles: 10 mi (Route B: 15 mi)."
    )


def test_explanation_says_high_or_unknown_when_missing_forecasts_counted() -> None:
    a = route("r1", "Route A", 300, [L, H, L])
    b = route("r2", "Route B", 200, [L, U, U, L])
    ranked, decided_by = rank([a, b])

    assert explain(ranked, decided_by) == [
        "All routes tie on Severe miles; "
        "Route A has the fewest High-or-unknown miles: 10 mi (Route B: 20 mi).",
        "+1 h 40 min vs the fastest route, Route B, which has more High-or-unknown miles (20 mi vs 10 mi).",
    ]


def test_explanation_when_all_routes_are_equally_safe() -> None:
    a = route("r1", "Route A", 432, [L, L, L])
    b = route("r2", "Route B", 450, [L, L, L])
    ranked, decided_by = rank([a, b])

    assert explain(ranked, decided_by) == [
        "All routes tie on Severe miles, High miles and average risk; Route A is the fastest (7 h 12 min).",
    ]


def test_explanation_for_high_miles_and_average_risk() -> None:
    hi = rank([route("r1", "Route A", 300, [L, H, H, L]), route("r2", "Route B", 290, [L, H, L, L])])
    avg = rank([route("r1", "Route A", 300, [M, M, L]), route("r2", "Route B", 310, [L, M, L])])

    assert explain(*hi)[0] == (
        "All routes tie on Severe miles; Route B has the fewest High miles: 10 mi (Route A: 20 mi)."
    )
    assert explain(*avg)[0] == (
        "All routes tie on Severe and High miles; Route B has the lowest average risk: 0.50 (Route A: 0.75)."
    )
    assert explain(*avg)[1] == (
        "+10 min vs the fastest route, Route A, which has a higher average risk (0.75 vs 0.50)."
    )


def test_a_tie_sentence_names_only_the_routes_that_actually_tie() -> None:
    # A is fastest but has a Moderate stretch; B and C are both all-Low, so travel time separates
    # B from C. A did not tie, and the sentence must not say it did.
    a = route("r1", "Route A", 477, [L, M, L, L])
    b = route("r2", "Route B", 490, [L, L, L, L])
    c = route("r3", "Route C", 507, [L, L, L, L])
    ranked, decided_by = rank([a, b, c])

    assert decided_by == "duration"
    assert explain(ranked, decided_by) == [
        "Route B and Route C tie on Severe miles, High miles and average risk; "
        "Route B is the faster of them (8 h 10 min).",
        "+13 min vs the fastest route, Route A, which has a higher average risk (0.33 vs 0.00).",
    ]


def test_mile_figures_in_sentences_keep_the_precision_that_decided_the_ranking() -> None:
    a = route("r1", "Route A", 300, [L, H, L])
    b = route("r2", "Route B", 310, [L, H, L])
    a.miles["high"], b.miles["high"] = 25.4, 25.2

    ranked, decided_by = rank([a, b])

    assert explain(ranked, decided_by) == [
        "All routes tie on Severe miles; Route B has the fewest High miles: 25.2 mi (Route A: 25.4 mi).",
        "+10 min vs the fastest route, Route A, which has more High miles (25.4 mi vs 25.2 mi).",
    ]


def test_a_route_a_few_seconds_slower_is_not_called_the_fastest() -> None:
    a = route("r1", "Route A", 60, [L, L, L])
    b = route("r2", "Route B", 60, [L, M, L])
    a.duration_s, b.duration_s = 3610, 3600

    ranked, decided_by = rank([a, b])

    assert ranked[0].id == "r1"
    assert explain(ranked, decided_by)[1] == (
        "+1 min vs the fastest route, Route B, which has a higher average risk (0.50 vs 0.00)."
    )


def test_identical_routes_are_described_as_a_full_tie() -> None:
    ranked, decided_by = rank([route("r1", "Route A", 300, [L, L]), route("r2", "Route B", 300, [L, L])])

    assert decided_by == "tie"
    assert explain(ranked, decided_by) == [
        "All routes tie on every criterion, including travel time; Route A is listed first."
    ]


# ---------------------------------------------------------------- warnings


def test_warnings_flag_no_travel_and_unknown_checkpoints() -> None:
    a = route("r1", "Route A", 300, [L, NT, L])  # 10 mi No Travel
    b = route("r2", "Route B", 360, [L, NT, NT, U, U, L])  # 20 mi No Travel, 2 without forecast
    ranked, _ = rank([a, b])

    assert ranked[0].id == "r1"
    assert warnings(ranked, recommended=ranked[0]) == [
        "Do not depart: the recommended route still crosses 10 mi of No-Travel conditions. "
        "Consider a later departure.",
        "Route B crosses 20 mi of No-Travel conditions.",
        "2 checkpoints on Route B have no forecast data. "
        "They are shown as Unknown and counted as High when ranking.",
    ]


def test_no_travel_on_a_non_recommended_route_is_a_plain_warning() -> None:
    a = route("r1", "Route A", 300, [L, L, L])
    b = route("r2", "Route B", 200, [L, NT, L])
    ranked, _ = rank([a, b])

    assert warnings(ranked, recommended=ranked[0]) == ["Route B crosses 10 mi of No-Travel conditions."]
