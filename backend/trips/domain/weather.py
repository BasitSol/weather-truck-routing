"""Hourly forecast for one grid cell, and reading it at an exact moment (D5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from trips.domain.models import LatLon, Weather

HOUR = timedelta(hours=1)


@dataclass(frozen=True)
class HourlyForecast:
    """Parallel hourly series; index i is the stamp `start_utc + i hours` (Open-Meteo, GMT).

    Open-Meteo semantics: wind is instantaneous at the stamp; gusts are the max of the preceding
    hour; rain, showers and snowfall are totals over the preceding hour (snowfall as snow depth,
    in inches). Values may be None where the model has no data.
    """

    cell: LatLon
    start_utc: datetime
    wind: list[float | None]
    gust: list[float | None]
    rain: list[float | None]
    showers: list[float | None]
    snow: list[float | None]

    def weather_at(self, t: datetime) -> Weather | None:
        """Conditions at moment `t`, or None if the forecast doesn't cover it.

        - Wind is linearly interpolated between the stamps either side of `t`.
        - Hourly totals are taken from the hour the truck is in, [floor(t), floor(t) + 1h),
          which Open-Meteo stamps at its end. Totals are never interpolated.
        """
        offset_h = (t - self.start_utc) / HOUR
        if offset_h < 0:
            return None
        k = int(offset_h)
        frac = offset_h - k
        bucket = k + 1  # stamp that closes the hour containing t
        if bucket >= len(self.wind):
            return None

        w0, w1 = self.wind[k], self.wind[k + 1]
        gust, rain, showers, snow = (
            self.gust[bucket],
            self.rain[bucket],
            self.showers[bucket],
            self.snow[bucket],
        )
        if w0 is None or w1 is None or rain is None or showers is None or snow is None:
            return None

        return Weather(
            wind_mph=w0 + frac * (w1 - w0),
            gust_mph=gust,
            rain_in_hr=rain + showers,
            snow_in_hr=snow,
        )
