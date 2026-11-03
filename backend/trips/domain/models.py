"""Domain types. Pure Python — nothing in trips.domain may import Django."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum


class Level(IntEnum):
    """Ordinal risk level. The integer is the score used for averages and the API."""

    UNKNOWN = -1
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {
    Level.UNKNOWN: "Unknown",
    Level.LOW: "Low",
    Level.MODERATE: "Moderate",
    Level.HIGH: "High",
    Level.SEVERE: "Severe",
    Level.NO_TRAVEL: "No Travel",
}

# Keys of Route.miles, in level order. "unknown" is last so the known levels read naturally.
MILES_KEYS: dict[Level, str] = {
    Level.LOW: "low",
    Level.MODERATE: "moderate",
    Level.HIGH: "high",
    Level.SEVERE: "severe",
    Level.NO_TRAVEL: "no_travel",
    Level.UNKNOWN: "unknown",
}


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float

    @property
    def pos(self) -> LatLon:
        return LatLon(self.lat, self.lon)


@dataclass(frozen=True)
class Weather:
    """Conditions at one place and time, in the brief's units."""

    wind_mph: float
    gust_mph: float | None  # informational only; never scored (D4)
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class RiskResult:
    level: Level
    levels: dict[str, Level]  # wind / rain / snow before the load rule; {} when unknown
    driver: str  # human sentence naming what set the level


@dataclass
class Checkpoint:
    mile: float
    pos: LatLon
    eta_utc: datetime
    owned_mi: float
    tz: str = "UTC"
    weather: Weather | None = None
    levels: dict[str, Level] = field(default_factory=dict)
    risk: Level = Level.UNKNOWN
    driver: str = ""


@dataclass(frozen=True)
class Segment:
    from_mi: float
    to_mi: float
    risk: Level


@dataclass
class Route:
    """One route option. `points`, `cum_mi` and `cum_s` are parallel arrays along the polyline."""

    id: str
    label: str
    points: list[LatLon]
    cum_mi: list[float]
    cum_s: list[float]
    length_mi: float
    duration_s: float
    notices: list[str] = field(default_factory=list)
    checkpoints: list[Checkpoint] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    miles: dict[str, float] = field(default_factory=dict)
    avg_risk: float | None = None
    worst: Level = Level.UNKNOWN

    @property
    def duration_min(self) -> float:
        return self.duration_s / 60


@dataclass(frozen=True)
class Recommendation:
    route_id: str
    ranking: list[str]
    decided_by: str  # severe_miles | high_miles | avg_risk | duration | tie
    reasons: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class HeatPoint:
    pos: LatLon
    r: list[int]  # one level per hour from departure; -1 unknown
