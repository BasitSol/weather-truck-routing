"""Run one live analysis and print a checkpoint table: `python manage.py analyze_demo`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from asgiref.sync import async_to_sync
from django.core.management.base import BaseCommand, CommandParser

from trips.domain.models import Level, Place
from trips.services import providers
from trips.services.analyze import TripRequest, analyze

DENVER = Place("Denver, CO", 39.7392, -104.9903)
SLC = Place("Salt Lake City, UT", 40.7608, -111.8910)


class Command(BaseCommand):
    help = "Analyze Denver → Salt Lake City with live routing and weather and print every checkpoint."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--load", type=int, default=44_000)
        parser.add_argument("--interval", type=int, default=25, choices=[10, 25, 50])
        parser.add_argument("--hours-ahead", type=int, default=18)

    def handle(self, *args: Any, **opts: Any) -> None:
        departure = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(
            hours=opts["hours_ahead"]
        )
        req = TripRequest(DENVER, SLC, departure, opts["load"], opts["interval"])
        a = async_to_sync(analyze)(req, providers.routing(), providers.weather())

        for r in a.routes:
            self.stdout.write(
                f"\n{r.label}  {r.length_mi:.1f} mi  {r.duration_min:.0f} min  avg={r.avg_risk}  "
                f"worst={r.worst.label}  miles={r.miles}"
            )
            for cp in r.checkpoints:
                local = cp.eta_utc.astimezone(ZoneInfo(cp.tz)).strftime("%a %H:%M %Z")
                w = cp.weather
                wx = (
                    "no data"
                    if w is None
                    else (
                        f"wind {w.wind_mph:5.1f}  gust {w.gust_mph or 0:5.1f}  "
                        f"rain {w.rain_in_hr:.2f}  snow {w.snow_in_hr:.2f}"
                    )
                )
                level = Level(cp.risk).label
                self.stdout.write(f"  {cp.mile:7.1f} mi  {local:<14} {wx:<52} {level:<9} {cp.driver}")
        rec = a.recommendation
        self.stdout.write(f"\nRecommended: {rec.route_id}  decided_by={rec.decided_by}")
        for line in rec.reasons + rec.warnings:
            self.stdout.write(f"  {line}")
        self.stdout.write(f"heat points={len(a.heat)}  timings={a.timings_ms}")
