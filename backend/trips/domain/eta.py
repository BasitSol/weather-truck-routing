"""When the truck reaches a given mile."""

from __future__ import annotations

from datetime import datetime, timedelta

from trips.domain.geo import interpolate


def time_at_mile(cum_mi: list[float], cum_s: list[float], mile: float) -> float:
    """Seconds after departure at `mile`, from the routing API's cumulative travel time.

    Continuous driving is assumed; hours-of-service breaks are out of scope (D16).
    """
    return interpolate(cum_mi, cum_s, mile)


def eta(departure_utc: datetime, seconds: float) -> datetime:
    return departure_utc + timedelta(seconds=round(seconds))
