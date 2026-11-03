"""Request validation (mirrors the form's rules) and response shaping (API.md §2.2)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from rest_framework import serializers

from trips.domain.geo import haversine_mi, simplify, slice_line
from trips.domain.heatmap import HEAT_HOURS
from trips.domain.models import Checkpoint, LatLon, Place, Route
from trips.domain.risk import round_half_up
from trips.domain.sampling import INTERVALS
from trips.services.analyze import Analysis, TripRequest
from trips.services.timezones import tz_at

MAX_LOAD_LB = 80_000  # US federal gross vehicle weight limit
DEPARTURE_PAST = timedelta(hours=1)
DEPARTURE_FUTURE = timedelta(days=14)


class PlaceSerializer(serializers.Serializer[Place]):
    label = serializers.CharField(min_length=1, max_length=200)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # "nan" parses as a float and slips past min/max, since every comparison with NaN is false.
        if not (math.isfinite(attrs["lat"]) and math.isfinite(attrs["lon"])):
            raise serializers.ValidationError("Coordinates must be finite numbers.")
        return attrs


class AnalyzeRequestSerializer(serializers.Serializer[TripRequest]):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure_at = serializers.CharField()
    load_lb = serializers.IntegerField(min_value=1, max_value=MAX_LOAD_LB)
    interval = serializers.ChoiceField(choices=INTERVALS, default=25)

    def validate_departure_at(self, value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Use an ISO-8601 date and time, e.g. 2026-11-03T08:00-07:00."
            ) from exc
        if parsed.tzinfo is None:
            raise serializers.ValidationError("Include a UTC offset so the departure time is unambiguous.")
        now = datetime.now(UTC)
        if parsed < now - DEPARTURE_PAST:
            raise serializers.ValidationError("Departure can't be in the past.")
        if parsed > now + DEPARTURE_FUTURE:
            raise serializers.ValidationError("Departure must be within the next 14 days (forecast range).")
        return parsed.astimezone(UTC)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        o, d = attrs["origin"], attrs["destination"]
        if haversine_mi(LatLon(o["lat"], o["lon"]), LatLon(d["lat"], d["lon"])) < 0.5:
            raise serializers.ValidationError(
                {"destination": ["Destination must be different from the origin."]}
            )
        return attrs

    def trip_request(self) -> TripRequest:
        v = self.validated_data
        return TripRequest(
            origin=Place(**v["origin"]),
            destination=Place(**v["destination"]),
            departure_utc=v["departure_at"],
            load_lb=v["load_lb"],
            interval=int(v["interval"]),
        )


class GeocodeQuerySerializer(serializers.Serializer[dict[str, Any]]):
    q = serializers.CharField(min_length=2, max_length=100, trim_whitespace=True)
    at = serializers.RegexField(r"^-?\d+(\.\d+)?,-?\d+(\.\d+)?$", required=False)
    limit = serializers.IntegerField(min_value=1, max_value=10, default=6)

    def bias(self) -> LatLon | None:
        at = self.validated_data.get("at")
        if not at:
            return None
        lat, lon = (float(x) for x in at.split(","))
        return LatLon(lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None


# ---------------------------------------------------------------------------- response


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _local(t: datetime, tz: str) -> str:
    return t.astimezone(ZoneInfo(tz)).isoformat(timespec="seconds")


def _coords(points: list[LatLon]) -> list[list[float]]:
    return [[round(p.lon, 5), round(p.lat, 5)] for p in simplify(points)]


def _checkpoint(i: int, cp: Checkpoint) -> dict[str, Any]:
    w = cp.weather
    return {
        "idx": i,
        "mile": round(cp.mile, 2),
        "lat": round(cp.pos.lat, 5),
        "lon": round(cp.pos.lon, 5),
        "tz": cp.tz,
        "eta_utc": _iso(cp.eta_utc),
        "eta_local": _local(cp.eta_utc, cp.tz),
        "owned_mi": round(cp.owned_mi, 2),
        "weather": None
        if w is None
        else {
            "wind_mph": round_half_up(w.wind_mph, "0.1"),
            "gust_mph": None if w.gust_mph is None else round_half_up(w.gust_mph, "0.1"),
            "rain_in_hr": round_half_up(w.rain_in_hr, "0.01"),
            "snow_in_hr": round_half_up(w.snow_in_hr, "0.01"),
        },
        "levels": {k: int(v) for k, v in cp.levels.items()},
        "risk": int(cp.risk),
        "driver": cp.driver,
    }


def _route(r: Route, departure_utc: datetime) -> dict[str, Any]:
    arrive = departure_utc + timedelta(seconds=r.duration_s)
    arrive_tz = r.checkpoints[-1].tz
    return {
        "id": r.id,
        "label": r.label,
        "summary": {
            "distance_mi": round(r.length_mi, 2),
            "duration_min": round(r.duration_min),
            "arrive_utc": _iso(arrive),
            "arrive_local": _local(arrive, arrive_tz),
            "arrive_tz": arrive_tz,
            "avg_risk": None if r.avg_risk is None else round(r.avg_risk, 2),
            "worst": int(r.worst),
            "miles": r.miles,
            "checkpoints": len(r.checkpoints),
        },
        "segments": [
            {
                "from_mi": round(s.from_mi, 2),
                "to_mi": round(s.to_mi, 2),
                "risk": int(s.risk),
                "coordinates": _coords(slice_line(r.points, r.cum_mi, s.from_mi, s.to_mi)),
            }
            for s in r.segments
        ],
        "checkpoints": [_checkpoint(i, cp) for i, cp in enumerate(r.checkpoints)],
        "notices": r.notices,
    }


def present(a: Analysis, request_id: str) -> dict[str, Any]:
    req = a.request
    origin_tz = tz_at(req.origin.pos)
    rec = a.recommendation
    return {
        "meta": {
            "request_id": request_id,
            "origin": req.origin.label,
            "destination": req.destination.label,
            "departure_utc": _iso(req.departure_utc),
            "departure_local": _local(req.departure_utc, origin_tz),
            "origin_tz": origin_tz,
            "interval_mi": req.interval,
            "load_lb": req.load_lb,
            "routing_provider": a.providers.get("routing"),
            "weather_provider": a.providers.get("weather"),
            "generated_at": _iso(datetime.now(UTC)),
            "timings_ms": a.timings_ms,
        },
        "routes": [_route(r, req.departure_utc) for r in a.routes],
        "recommendation": {
            "route_id": rec.route_id,
            "ranking": rec.ranking,
            "decided_by": rec.decided_by,
            "reasons": rec.reasons,
            "warnings": rec.warnings,
        },
        "heatmap": {
            "start_utc": _iso(req.departure_utc),
            "hours": HEAT_HOURS,
            "points": [{"lat": p.pos.lat, "lon": p.pos.lon, "r": p.r} for p in a.heat],
        },
    }
