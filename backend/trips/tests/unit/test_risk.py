"""Risk classification — the brief's threshold table and load rules, boundary by boundary.

Every row here is traceable to SPEC §2.6. Boundaries are lower-bound inclusive; the top of
Severe is inclusive for rain and snow because No Travel is defined as strictly greater.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from trips.domain.models import Level, Weather
from trips.domain.risk import (
    apply_load_rules,
    checkpoint_risk,
    rain_level,
    snow_level,
    wind_level,
)

L, M, H, S, NT = Level.LOW, Level.MODERATE, Level.HIGH, Level.SEVERE, Level.NO_TRAVEL


def wx(wind: float = 0.0, rain: float = 0.0, snow: float = 0.0) -> Weather:
    return Weather(wind_mph=wind, gust_mph=wind, rain_in_hr=rain, snow_in_hr=snow)


@pytest.mark.parametrize(
    ("mph", "expected"),
    [
        (0.0, L),
        (24.9, L),
        (25.0, M),
        (34.9, M),
        (35.0, H),
        (44.9, H),
        (45.0, S),
        (54.9, S),
        (55.0, NT),
        (80.0, NT),
    ],
)
def test_wind_bands_are_lower_bound_inclusive(mph: float, expected: Level) -> None:
    assert wind_level(mph) == expected


def test_wind_between_integer_bands_is_classified_continuously() -> None:
    # The brief writes 25–34 and 35–44; decimal forecasts in the gap must still classify.
    assert wind_level(34.6) == M
    assert wind_level(34.96) == H  # rounds to 35.0 before comparing


@pytest.mark.parametrize(
    ("inhr", "expected"),
    [(0.0, L), (0.09, L), (0.10, M), (0.24, M), (0.25, H), (0.49, H), (0.50, S), (1.00, S), (1.01, NT)],
)
def test_rain_bands_with_inclusive_top_of_severe(inhr: float, expected: Level) -> None:
    assert rain_level(inhr) == expected


def test_rain_rounds_to_two_decimals_before_comparing() -> None:
    assert rain_level(0.249999) == H
    assert rain_level(0.0949) == L


@pytest.mark.parametrize(
    ("inhr", "expected"),
    [(0.0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, NT)],
)
def test_snow_bands_with_inclusive_top_of_severe(inhr: float, expected: Level) -> None:
    assert snow_level(inhr) == expected


@pytest.mark.parametrize(
    ("mph", "load_lb", "expected"),
    [
        (40.0, 40_000, H),  # L3 is strict: exactly 40,000 lb does not trigger
        (40.0, 40_001, S),
        (35.0, 40_001, S),
        (44.9, 80_000, S),
        (50.0, 30_000, S),  # L2 is strict: exactly 30,000 lb does not trigger
        (50.0, 30_001, NT),
        (45.0, 30_001, NT),
        (55.0, 1, NT),  # L1: any load
        (20.0, 80_000, L),  # load rules never touch calm wind
        (30.0, 80_000, M),
    ],
)
def test_load_rules(mph: float, load_lb: int, expected: Level) -> None:
    assert apply_load_rules(wind_level(mph), mph, load_lb) == expected


def test_load_rule_rounds_wind_before_comparing() -> None:
    # 44.95 rounds to 45.0 → Severe band → >30,000 lb → No Travel
    assert apply_load_rules(wind_level(44.95), 44.95, 30_001) == NT


def test_worst_condition_wins_and_wind_is_reported_first_on_a_tie() -> None:
    result = checkpoint_risk(wx(wind=40, rain=0.6), load_lb=45_000)

    assert result.level == S
    assert result.driver == "Wind 40.0 mph with 45,000 lb load (> 40,000 lb) → Severe"


def test_snow_drives_when_it_is_the_worst_condition() -> None:
    result = checkpoint_risk(wx(wind=10, rain=0.3, snow=2.5), load_lb=20_000)

    assert result.level == S
    assert result.driver == "Snow 2.50 in/hr → Severe"
    assert result.levels == {"wind": L, "rain": H, "snow": S}


def test_per_condition_levels_are_reported_before_the_load_rule() -> None:
    result = checkpoint_risk(wx(wind=40), load_lb=45_000)

    assert result.levels["wind"] == H
    assert result.level == S


def test_load_rule_driver_names_the_weight_threshold() -> None:
    result = checkpoint_risk(wx(wind=50), load_lb=36_000)

    assert result.level == NT
    assert result.driver == "Wind 50.0 mph with 36,000 lb load (> 30,000 lb) → No Travel"


def test_calm_dry_checkpoint_is_low_with_a_plain_driver() -> None:
    result = checkpoint_risk(wx(wind=8.2, rain=0.0), load_lb=44_000)

    assert result.level == L
    assert result.driver == "Wind 8.2 mph → Low"


def test_rain_driver_sentence() -> None:
    assert checkpoint_risk(wx(rain=0.62), load_lb=10_000).driver == "Rain 0.62 in/hr → Severe"


def test_missing_weather_is_unknown_never_low() -> None:
    result = checkpoint_risk(None, load_lb=44_000)

    assert result.level == Level.UNKNOWN
    assert result.levels == {}
    assert result.driver == "No forecast available for this time and place"


weather_values = st.floats(min_value=0, max_value=120, allow_nan=False)
precip_values = st.floats(min_value=0, max_value=5, allow_nan=False)
loads = st.integers(min_value=1, max_value=80_000)


@given(
    wind=weather_values,
    rain=precip_values,
    snow=precip_values,
    load=loads,
    d_wind=st.floats(min_value=0, max_value=30),
    d_rain=st.floats(min_value=0, max_value=1),
    d_snow=st.floats(min_value=0, max_value=1),
    d_load=st.integers(min_value=0, max_value=40_000),
)
def test_raising_any_input_never_lowers_risk(
    wind: float,
    rain: float,
    snow: float,
    load: int,
    d_wind: float,
    d_rain: float,
    d_snow: float,
    d_load: int,
) -> None:
    base = checkpoint_risk(wx(wind, rain, snow), load).level
    worse = checkpoint_risk(wx(wind + d_wind, rain + d_rain, snow + d_snow), min(load + d_load, 80_000)).level

    assert worse >= base
