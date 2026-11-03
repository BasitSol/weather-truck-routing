"""POST /api/v1/analyze end to end, with recorded routing and synthetic weather (API.md §2)."""

import itertools
from collections.abc import Iterator
from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client

from trips.domain.models import Place
from trips.providers.base import NoRouteError, ProviderError, RateLimitedError
from trips.providers.fakes import FixedGeocoder, RecordedRouting, SyntheticWeather
from trips.services import providers

FIXTURE = Path(__file__).parent.parent / "fixtures" / "valhalla_den_slc.json"


@pytest.fixture(autouse=True)
def _clean_cache() -> Iterator[None]:
    cache.clear()
    yield
    cache.clear()


def tomorrow_8am() -> str:
    mst = timezone(timedelta(hours=-7))
    return datetime.combine((datetime.now(mst) + timedelta(days=1)).date(), time(8), mst).isoformat()


def trip(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "origin": {"label": "Denver, CO", "lat": 39.7392, "lon": -104.9903},
        "destination": {"label": "Salt Lake City, UT", "lat": 40.7608, "lon": -111.8910},
        "departure_at": tomorrow_8am(),
        "load_lb": 44_000,
        "interval": 25,
    }
    body.update(overrides)
    return body


def post(client: Client, body: dict[str, Any]) -> Any:
    return client.post("/api/v1/analyze", body, content_type="application/json")


@pytest.fixture
def fakes() -> Iterator[SyntheticWeather]:
    weather = SyntheticWeather()
    with providers.override(routing=RecordedRouting(FIXTURE), weather=weather):
        yield weather


def test_analysis_returns_three_routes_honouring_every_api_invariant(
    client: Client, fakes: SyntheticWeather
) -> None:
    res = post(client, trip())

    assert res.status_code == 200
    data = res.json()
    routes = data["routes"]
    assert [r["label"] for r in routes] == ["Route A", "Route B", "Route C"]
    rec = data["recommendation"]
    assert sorted(rec["ranking"]) == sorted(r["id"] for r in routes)
    assert rec["route_id"] == rec["ranking"][0]
    for r in routes:
        length = r["summary"]["distance_mi"]
        segs = r["segments"]
        assert segs[0]["from_mi"] == 0
        assert (
            segs[-1]["to_mi"] == length
        )  # same precision as distance_mi, so the last checkpoint is inside it
        assert all(
            round(g["from_mi"], 2) == g["from_mi"] and round(g["to_mi"], 2) == g["to_mi"] for g in segs
        )
        assert all(a["to_mi"] == pytest.approx(b["from_mi"]) for a, b in itertools.pairwise(segs))
        assert all(len(s["coordinates"]) >= 2 for s in segs)
        cps = r["checkpoints"]
        assert cps[0]["mile"] == 0 and cps[-1]["mile"] == pytest.approx(length, abs=0.01)
        assert sum(c["owned_mi"] for c in cps) == pytest.approx(length, abs=0.05)
        assert sum(r["summary"]["miles"].values()) == pytest.approx(length, abs=0.05)
        etas = [c["eta_utc"] for c in cps]
        assert etas == sorted(etas)
    heat = data["heatmap"]
    assert heat["hours"] == 48
    assert heat["points"]
    assert all(len(p["r"]) == 49 and set(p["r"]) <= {-1, 0, 1, 2, 3, 4} for p in heat["points"])
    assert data["meta"]["load_lb"] == 44_000 and data["meta"]["interval_mi"] == 25


def test_checkpoints_carry_weather_level_driver_and_local_time(
    client: Client, fakes: SyntheticWeather
) -> None:
    data = post(client, trip()).json()

    windy = [c for r in data["routes"] for c in r["checkpoints"] if c["lat"] > 41.05]
    assert windy, "the recorded I-80 route crosses Wyoming"
    cp = windy[0]
    assert cp["weather"]["wind_mph"] == 40.0
    assert cp["levels"] == {"wind": 2, "rain": 0, "snow": 0}
    assert cp["risk"] == 3
    assert cp["driver"] == "Wind 40.0 mph with 44,000 lb load (> 40,000 lb) → Severe"
    assert cp["tz"] == "America/Denver"
    assert cp["eta_local"].endswith("-07:00")


def test_load_weight_flips_wind_40_checkpoints_between_high_and_severe(
    client: Client, fakes: SyntheticWeather
) -> None:
    light = post(client, trip(load_lb=35_000)).json()
    heavy = post(client, trip(load_lb=45_000)).json()

    def windy_levels(data: dict[str, Any]) -> set[int]:
        return {c["risk"] for r in data["routes"] for c in r["checkpoints"] if c["lat"] > 41.05}

    assert windy_levels(light) == {2}
    assert windy_levels(heavy) == {3}


def test_the_recommended_route_avoids_the_severe_corridor(client: Client, fakes: SyntheticWeather) -> None:
    data = post(client, trip()).json()
    by_id = {r["id"]: r for r in data["routes"]}
    rec = data["recommendation"]

    severe = [r for r in data["routes"] if r["summary"]["miles"]["severe"] > 0]
    assert len(severe) == 1, "only the Wyoming route crosses the synthetic wind"
    assert by_id[rec["route_id"]]["summary"]["miles"]["severe"] == 0
    assert rec["ranking"][-1] == severe[0]["id"]
    # Both I-70 routes have 0 Severe and 0 High miles, so a later criterion separates them.
    assert rec["decided_by"] in {"avg_risk", "duration"}


def test_weather_is_requested_once_per_grid_cell(client: Client, fakes: SyntheticWeather) -> None:
    post(client, trip())

    assert len(fakes.requested) == len(set(fakes.requested))


def test_partial_weather_failure_shows_unknown_checkpoints_and_a_warning(client: Client) -> None:
    weather = SyntheticWeather(missing=lambda c: 40.0 < c.lat < 40.5 and c.lon > -106.0)
    with providers.override(routing=RecordedRouting(FIXTURE), weather=weather):
        res = post(client, trip(interval=10))

    assert res.status_code == 200
    data = res.json()
    unknown = [c for r in data["routes"] for c in r["checkpoints"] if c["risk"] == -1]
    assert unknown
    assert all(c["weather"] is None and c["levels"] == {} for c in unknown)
    assert any("no forecast data" in w for w in data["recommendation"]["warnings"])


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"departure_at": "2026-11-03T08:00:00"}, "departure_at"),
        ({"departure_at": (datetime.now(UTC) + timedelta(days=20)).isoformat()}, "departure_at"),
        ({"departure_at": (datetime.now(UTC) - timedelta(hours=3)).isoformat()}, "departure_at"),
        ({"load_lb": 0}, "load_lb"),
        ({"load_lb": 80_001}, "load_lb"),
        ({"interval": 30}, "interval"),
        ({"destination": {"label": "Denver", "lat": 39.7393, "lon": -104.9904}}, "destination"),
        ({"origin": {"label": "Nowhere", "lat": 95, "lon": 0}}, "origin"),
        ({"origin": {"label": "Not a number", "lat": "nan", "lon": "nan"}}, "origin"),
        ({"destination": {"label": "Infinity", "lat": "inf", "lon": 0}}, "destination"),
    ],
)
def test_invalid_input_is_a_400_naming_the_field(
    client: Client, fakes: SyntheticWeather, overrides: dict[str, Any], field: str
) -> None:
    res = post(client, trip(**overrides))

    assert res.status_code == 400
    body = res.json()["error"]
    assert body["code"] == "validation_error"
    assert field in body["fields"]


def test_no_truck_route_is_a_404(client: Client) -> None:
    with providers.override(
        routing=RecordedRouting(FIXTURE, error=NoRouteError("No path")), weather=SyntheticWeather()
    ):
        res = post(client, trip())

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "no_route"


def test_routing_outage_is_a_502(client: Client) -> None:
    with providers.override(
        routing=RecordedRouting(FIXTURE, error=ProviderError("valhalla", "HTTP 503", 503)),
        weather=SyntheticWeather(),
    ):
        res = post(client, trip())

    assert res.status_code == 502
    assert res.json()["error"]["code"] == "routing_unavailable"


def test_total_weather_outage_is_a_502_not_a_silent_low(client: Client) -> None:
    with providers.override(
        routing=RecordedRouting(FIXTURE), weather=SyntheticWeather(missing=lambda c: True)
    ):
        res = post(client, trip())

    assert res.status_code == 502
    assert res.json()["error"]["code"] == "weather_unavailable"


def test_a_rate_limited_weather_service_is_a_503_asking_to_retry(client: Client) -> None:
    class Throttled(SyntheticWeather):
        async def hourly(self, cells, start_utc, end_utc):  # type: ignore[no-untyped-def]
            raise RateLimitedError("open-meteo", "HTTP 429", 429)

    with providers.override(routing=RecordedRouting(FIXTURE), weather=Throttled()):
        res = post(client, trip())

    assert res.status_code == 503
    body = res.json()["error"]
    assert body["code"] == "weather_busy"
    assert "try again in a minute" in body["message"].lower()


def test_a_rate_limited_routing_service_is_reported_as_routing_not_weather(client: Client) -> None:
    class ThrottledRouting:
        name = "valhalla"

        async def routes(self, origin, destination, gross_lb, via=None):  # type: ignore[no-untyped-def]
            raise RateLimitedError("valhalla", "HTTP 429", 429)

    with providers.override(routing=ThrottledRouting(), weather=SyntheticWeather()):
        res = post(client, trip())

    assert res.status_code == 503
    assert res.json()["error"]["code"] == "routing_busy"


def test_health(client: Client) -> None:
    res = client.get("/api/v1/health")

    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_geocode_returns_places_with_their_timezone(client: Client) -> None:
    slc = Place("Salt Lake City, Utah, US", 40.7608, -111.891)
    with providers.override(geocoder=FixedGeocoder([slc])):
        res = client.get("/api/v1/geocode", {"q": "salt lake"})

    assert res.status_code == 200
    assert res.json() == {
        "results": [
            {"label": "Salt Lake City, Utah, US", "lat": 40.7608, "lon": -111.891, "tz": "America/Denver"}
        ]
    }


def test_geocode_rejects_a_one_letter_query(client: Client) -> None:
    res = client.get("/api/v1/geocode", {"q": "s"})

    assert res.status_code == 400
    assert "q" in res.json()["error"]["fields"]
