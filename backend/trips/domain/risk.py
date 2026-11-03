"""Checkpoint risk classification — the brief's threshold table and load rules.

Conventions (docs/DECISIONS.md D2, D3, D6, D7):
- Every band is lower-bound inclusive. Wind bands written as integers (25–34, 35–44) are treated
  as continuous half-open intervals so decimal forecasts are never unclassified.
- No Travel for rain and snow is strictly greater than the Severe top (> 1.00, > 3.0), so the top
  of Severe is inclusive.
- Values are rounded half-up (wind 1 dp, precipitation 2 dp) before comparison, so float noise
  such as 0.249999 never flips a band.
- Load rules apply to wind only, compare weight with strict `>`, and can only raise a level.
- A checkpoint's risk is the worst of wind (after load rules), rain and snow.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from trips.domain.models import Level, RiskResult, Weather

LOAD_NO_TRAVEL_LB = 30_000  # 45–54 mph + > 30,000 lb → No Travel
LOAD_SEVERE_LB = 40_000  # 35–44 mph + > 40,000 lb → Severe


def round_half_up(value: float, places: str) -> float:
    """Round as a person would (0.125 → 0.13), via Decimal so float noise never flips a band."""
    return float(Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def wind_level(mph: float) -> Level:
    mph = round_half_up(mph, "0.1")
    if mph >= 55:
        return Level.NO_TRAVEL
    if mph >= 45:
        return Level.SEVERE
    if mph >= 35:
        return Level.HIGH
    if mph >= 25:
        return Level.MODERATE
    return Level.LOW


def rain_level(in_hr: float) -> Level:
    in_hr = round_half_up(in_hr, "0.01")
    if in_hr > 1.00:
        return Level.NO_TRAVEL
    if in_hr >= 0.50:
        return Level.SEVERE
    if in_hr >= 0.25:
        return Level.HIGH
    if in_hr >= 0.10:
        return Level.MODERATE
    return Level.LOW


def snow_level(in_hr: float) -> Level:
    in_hr = round_half_up(in_hr, "0.01")
    if in_hr > 3.0:
        return Level.NO_TRAVEL
    if in_hr >= 2.0:
        return Level.SEVERE
    if in_hr >= 1.0:
        return Level.HIGH
    if in_hr >= 0.5:
        return Level.MODERATE
    return Level.LOW


def apply_load_rules(level: Level, mph: float, load_lb: int) -> Level:
    """Raise a wind level for heavy loads. Never lowers it."""
    mph = round_half_up(mph, "0.1")
    if mph >= 55:
        return Level.NO_TRAVEL
    if 45 <= mph < 55 and load_lb > LOAD_NO_TRAVEL_LB:
        return Level.NO_TRAVEL
    if 35 <= mph < 45 and load_lb > LOAD_SEVERE_LB:
        return max(level, Level.SEVERE)
    return level


def _load_threshold_hit(mph: float, load_lb: int) -> int | None:
    """The weight threshold that a load rule used to raise this wind, if any."""
    mph = round_half_up(mph, "0.1")
    if 45 <= mph < 55 and load_lb > LOAD_NO_TRAVEL_LB:
        return LOAD_NO_TRAVEL_LB
    if 35 <= mph < 45 and load_lb > LOAD_SEVERE_LB:
        return LOAD_SEVERE_LB
    return None


def checkpoint_risk(weather: Weather | None, load_lb: int) -> RiskResult:
    """Classify one checkpoint. Missing weather is Unknown — never Low (D13)."""
    if weather is None:
        return RiskResult(Level.UNKNOWN, {}, "No forecast available for this time and place")

    levels = {
        "wind": wind_level(weather.wind_mph),
        "rain": rain_level(weather.rain_in_hr),
        "snow": snow_level(weather.snow_in_hr),
    }
    wind_after_load = apply_load_rules(levels["wind"], weather.wind_mph, load_lb)
    level = max(wind_after_load, levels["rain"], levels["snow"])

    # Deterministic driver order on ties: wind, then rain, then snow.
    if wind_after_load == level:
        mph = round_half_up(weather.wind_mph, "0.1")
        threshold = (
            _load_threshold_hit(weather.wind_mph, load_lb) if wind_after_load > levels["wind"] else None
        )
        load_note = f" with {load_lb:,} lb load (> {threshold:,} lb)" if threshold else ""
        driver = f"Wind {mph:.1f} mph{load_note} → {level.label}"
    elif levels["rain"] == level:
        driver = f"Rain {round_half_up(weather.rain_in_hr, '0.01'):.2f} in/hr → {level.label}"
    else:
        driver = f"Snow {round_half_up(weather.snow_in_hr, '0.01'):.2f} in/hr → {level.label}"

    return RiskResult(level, levels, driver)
