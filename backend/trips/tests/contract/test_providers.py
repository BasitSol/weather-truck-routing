"""Provider adapters: parsing real recorded responses and mapping upstream failures."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from trips.domain.models import LatLon, Place
from trips.providers.base import NoRouteError, ProviderError, RateLimitedError
from trips.providers.open_meteo import OpenMeteoWeather
from trips.providers.photon import PhotonGeocoder
from trips.providers.polyline import decode
from trips.providers.valhalla import FallbackRouting, ValhallaRouting

FIXTURES = Path(__file__).parent.parent / "fixtures"
VALHALLA = "https://valhalla.test/route"
OPEN_METEO = "https://open-meteo.test/v1/forecast"
PHOTON = "https://photon.test/api/"
DENVER = Place("Denver, CO", 39.7392, -104.9903)
SLC = Place("Salt Lake City, UT", 40.7608, -111.8910)


def test_polyline_decodes_the_reference_example() -> None:
    # Google's reference string, read at precision 5.
    assert decode("_p~iF~ps|U_ulLnnqC_mqNvxq`@", precision=5) == [
        LatLon(38.5, -120.2),
        LatLon(40.7, -120.95),
        LatLon(43.252, -126.453),
    ]


@respx.mock
async def test_valhalla_returns_main_route_and_alternates_as_routes() -> None:
    respx.post(VALHALLA).mock(
        return_value=httpx.Response(200, json=json.loads((FIXTURES / "valhalla_den_slc.json").read_text()))
    )

    routes = await ValhallaRouting(VALHALLA).routes(DENVER, SLC, gross_lb=44_000)

    assert [r.id for r in routes] == ["r1", "r2", "r3"]
    assert [r.label for r in routes] == ["Route A", "Route B", "Route C"]
    for r in routes:
        assert r.cum_mi[0] == 0 and r.cum_mi[-1] == pytest.approx(r.length_mi)
        assert r.cum_s[0] == 0 and r.cum_s[-1] == pytest.approx(r.duration_s)
        assert all(b >= a for a, b in zip(r.cum_s, r.cum_s[1:], strict=False))
        assert abs(r.points[0].lat - DENVER.lat) < 0.1 and abs(r.points[-1].lat - SLC.lat) < 0.1


@respx.mock
async def test_valhalla_sends_truck_costing_with_weight_in_metric_tons() -> None:
    route = respx.post(VALHALLA).mock(
        return_value=httpx.Response(200, json=json.loads((FIXTURES / "valhalla_den_slc.json").read_text()))
    )

    await ValhallaRouting(VALHALLA).routes(DENVER, SLC, gross_lb=44_000)

    sent = json.loads(route.calls.last.request.content)
    assert sent["costing"] == "truck"
    assert sent["alternates"] == 2
    assert sent["costing_options"]["truck"]["weight"] == pytest.approx(19.96, abs=0.01)


@respx.mock
async def test_valhalla_routes_through_a_waypoint_without_stopping_and_asks_for_one_route() -> None:
    route = respx.post(VALHALLA).mock(
        return_value=httpx.Response(200, json=json.loads((FIXTURES / "valhalla_den_slc.json").read_text()))
    )

    await ValhallaRouting(VALHALLA).routes(DENVER, SLC, gross_lb=44_000, via=LatLon(40.5, -108.0))

    sent = json.loads(route.calls.last.request.content)
    assert sent["locations"][1] == {"lat": 40.5, "lon": -108.0, "type": "through"}
    assert [loc["lat"] for loc in sent["locations"]] == [DENVER.lat, 40.5, SLC.lat]
    assert sent["alternates"] == 0


@respx.mock
async def test_fallback_passes_a_waypoint_to_the_primary_without_topping_up() -> None:
    payload = json.loads((FIXTURES / "valhalla_den_slc.json").read_text())
    payload["alternates"] = []
    primary_route = respx.post("https://primary.test/route").mock(
        return_value=httpx.Response(200, json=payload)
    )
    secondary_route = respx.post(VALHALLA).mock(return_value=httpx.Response(200, json=payload))
    routing = FallbackRouting(ValhallaRouting("https://primary.test/route"), ValhallaRouting(VALHALLA))

    routes = await routing.routes(DENVER, SLC, 44_000, via=LatLon(40.5, -108.0))

    assert len(routes) == 1
    assert primary_route.called and not secondary_route.called


@respx.mock
async def test_valhalla_no_path_is_a_no_route_error() -> None:
    respx.post(VALHALLA).mock(
        return_value=httpx.Response(
            400, json={"error_code": 442, "error": "No path could be found for input"}
        )
    )

    with pytest.raises(NoRouteError):
        await ValhallaRouting(VALHALLA).routes(DENVER, SLC, gross_lb=44_000)


@respx.mock
async def test_upstream_5xx_is_retried_then_succeeds() -> None:
    payload = json.loads((FIXTURES / "valhalla_den_slc.json").read_text())
    respx.post(VALHALLA).mock(side_effect=[httpx.Response(503), httpx.Response(200, json=payload)])

    routes = await ValhallaRouting(VALHALLA, backoff_s=0).routes(DENVER, SLC, gross_lb=44_000)

    assert len(routes) == 3


@respx.mock
async def test_upstream_that_keeps_failing_is_a_provider_error() -> None:
    respx.post(VALHALLA).mock(return_value=httpx.Response(502))

    with pytest.raises(ProviderError) as exc:
        await ValhallaRouting(VALHALLA, backoff_s=0).routes(DENVER, SLC, gross_lb=44_000)

    assert exc.value.provider == "valhalla"


def _om_location(lat: float, lon: float, wind: float) -> dict:
    return {
        "latitude": lat,
        "longitude": lon,
        "hourly": {
            "time": ["2026-11-03T15:00", "2026-11-03T16:00", "2026-11-03T17:00"],
            "wind_speed_10m": [wind, wind, wind],
            "wind_gusts_10m": [wind + 10] * 3,
            "rain": [0.0, 0.1, 0.0],
            "showers": [0.0, 0.0, 0.0],
            "snowfall": [0.0, 0.0, 0.0],
        },
    }


START = datetime(2026, 11, 3, 15, tzinfo=UTC)
END = datetime(2026, 11, 3, 17, tzinfo=UTC)


@respx.mock
async def test_open_meteo_many_locations_map_back_to_requested_cells_in_order() -> None:
    cells = [LatLon(39.75, -105.0), LatLon(41.15, -104.8)]
    route = respx.get(OPEN_METEO).mock(
        return_value=httpx.Response(
            200, json=[_om_location(39.746, -104.987, 12), _om_location(41.14, -104.8, 30)]
        )
    )

    out = await OpenMeteoWeather(OPEN_METEO).hourly(cells, START, END)

    assert out[cells[0]].wind[0] == 12 and out[cells[1]].wind[0] == 30
    assert out[cells[0]].start_utc == START
    params = route.calls.last.request.url.params
    assert params["wind_speed_unit"] == "mph" and params["precipitation_unit"] == "inch"
    assert params["timezone"] == "GMT" and params["start_hour"] == "2026-11-03T15:00"
    assert "showers" in params["hourly"] and "precipitation" not in params["hourly"].split(",")


@respx.mock
async def test_open_meteo_single_location_returns_an_object_not_a_list() -> None:
    cell = LatLon(39.75, -105.0)
    respx.get(OPEN_METEO).mock(return_value=httpx.Response(200, json=_om_location(39.746, -104.987, 7)))

    out = await OpenMeteoWeather(OPEN_METEO).hourly([cell], START, END)

    assert out[cell].wind == [7, 7, 7]


@respx.mock
async def test_a_failed_weather_chunk_leaves_only_its_cells_missing() -> None:
    cells = [LatLon(40.0 + i * 0.05, -105.0) for i in range(3)]

    def upstream(request: httpx.Request) -> httpx.Response:
        if request.url.params["latitude"] == "40.1":  # the second chunk always fails
            return httpx.Response(500)
        return httpx.Response(200, json=[_om_location(c.lat, c.lon, 5) for c in cells[:2]])

    respx.get(OPEN_METEO).mock(side_effect=upstream)

    out = await OpenMeteoWeather(OPEN_METEO, chunk_size=2, backoff_s=0).hourly(cells, START, END)

    assert set(out) == set(cells[:2])


@respx.mock
async def test_a_rate_limited_weather_chunk_fails_the_whole_request_instead_of_leaving_gaps() -> None:
    cells = [LatLon(40.0 + i * 0.05, -105.0) for i in range(3)]

    def upstream(request: httpx.Request) -> httpx.Response:
        if request.url.params["latitude"] == "40.1":  # the second chunk is refused for rate limiting
            return httpx.Response(429)
        return httpx.Response(200, json=[_om_location(c.lat, c.lon, 5) for c in cells[:2]])

    respx.get(OPEN_METEO).mock(side_effect=upstream)

    # Throttled cells are not "no forecast": scoring them as Unknown would skew the ranking.
    with pytest.raises(RateLimitedError):
        await OpenMeteoWeather(OPEN_METEO, chunk_size=2, backoff_s=0).hourly(cells, START, END)


@respx.mock
async def test_photon_suggestions_are_labelled_places() -> None:
    respx.get(PHOTON).mock(
        return_value=httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {"coordinates": [-111.891, 40.7608]},
                        "properties": {"name": "Salt Lake City", "state": "Utah", "countrycode": "US"},
                    },
                    {"geometry": {"coordinates": [-111.9, 40.7]}, "properties": {}},
                ]
            },
        )
    )

    places = await PhotonGeocoder(PHOTON).suggest("salt lake", at=None, limit=6)

    assert places == [Place("Salt Lake City, Utah, US", 40.7608, -111.891)]


@respx.mock
async def test_photon_failure_returns_no_suggestions() -> None:
    respx.get(PHOTON).mock(return_value=httpx.Response(503))

    assert await PhotonGeocoder(PHOTON, backoff_s=0).suggest("salt lake", at=None, limit=6) == []


@respx.mock
async def test_a_weather_chunk_rejected_with_a_4xx_is_left_missing_not_raised() -> None:
    cells = [LatLon(40.0, -105.0)]
    respx.get(OPEN_METEO).mock(
        return_value=httpx.Response(400, json={"error": True, "reason": "out of range"})
    )

    assert await OpenMeteoWeather(OPEN_METEO, backoff_s=0).hourly(cells, START, END) == {}


@respx.mock
async def test_a_malformed_weather_payload_is_left_missing_not_raised() -> None:
    cells = [LatLon(40.0, -105.0)]
    respx.get(OPEN_METEO).mock(return_value=httpx.Response(200, json={"latitude": 40}))

    assert await OpenMeteoWeather(OPEN_METEO, backoff_s=0).hourly(cells, START, END) == {}


@respx.mock
async def test_valhalla_distance_limit_is_reported_as_such() -> None:
    respx.post(VALHALLA).mock(
        return_value=httpx.Response(
            400, json={"error_code": 154, "error": "Path distance exceeds the max distance limit"}
        )
    )

    with pytest.raises(NoRouteError, match="longer than the routing service supports"):
        await ValhallaRouting(VALHALLA).routes(DENVER, SLC, gross_lb=44_000)


@respx.mock
async def test_valhalla_sends_the_api_key_when_one_is_configured() -> None:
    route = respx.post(VALHALLA).mock(
        return_value=httpx.Response(200, json=json.loads((FIXTURES / "valhalla_den_slc.json").read_text()))
    )

    await ValhallaRouting(VALHALLA, api_key="stadia-test-key").routes(DENVER, SLC, gross_lb=44_000)

    assert route.calls.last.request.url.params["api_key"] == "stadia-test-key"


@respx.mock
async def test_valhalla_sends_no_key_to_the_keyless_server() -> None:
    route = respx.post(VALHALLA).mock(
        return_value=httpx.Response(200, json=json.loads((FIXTURES / "valhalla_den_slc.json").read_text()))
    )

    await ValhallaRouting(VALHALLA).routes(DENVER, SLC, gross_lb=44_000)

    assert "api_key" not in route.calls.last.request.url.params


@respx.mock
async def test_routing_falls_back_to_the_second_provider_when_the_first_is_down() -> None:
    respx.post("https://primary.test/route").mock(return_value=httpx.Response(503))
    respx.post(VALHALLA).mock(
        return_value=httpx.Response(200, json=json.loads((FIXTURES / "valhalla_den_slc.json").read_text()))
    )
    routing = FallbackRouting(
        ValhallaRouting("https://primary.test/route", api_key="k", backoff_s=0), ValhallaRouting(VALHALLA)
    )

    routes = await routing.routes(DENVER, SLC, gross_lb=44_000)

    assert len(routes) == 3


@respx.mock
async def test_no_route_is_an_answer_not_an_outage_so_there_is_no_fallback() -> None:
    respx.post("https://primary.test/route").mock(
        return_value=httpx.Response(400, json={"error_code": 442, "error": "No path could be found"})
    )
    secondary = respx.post(VALHALLA).mock(return_value=httpx.Response(200, json={}))
    routing = FallbackRouting(ValhallaRouting("https://primary.test/route"), ValhallaRouting(VALHALLA))

    with pytest.raises(NoRouteError):
        await routing.routes(DENVER, SLC, gross_lb=44_000)
    assert not secondary.called


@respx.mock
async def test_a_response_without_maneuvers_spreads_leg_time_by_distance() -> None:
    # Recorded from Stadia Maps' hosted Valhalla, which omits maneuvers when narrative is off.
    payload = json.loads((FIXTURES / "stadia_den_slc.json").read_text())
    assert "maneuvers" not in payload["trip"]["legs"][0]
    respx.post(VALHALLA).mock(return_value=httpx.Response(200, json=payload))

    routes = await ValhallaRouting(VALHALLA).routes(DENVER, SLC, gross_lb=44_000)

    assert len(routes) == 3
    for r in routes:
        assert r.cum_s[0] == 0 and r.cum_s[-1] == pytest.approx(r.duration_s)
        assert all(b >= a for a, b in zip(r.cum_s, r.cum_s[1:], strict=False))
        mid = len(r.cum_mi) // 2  # constant speed: time share equals distance share
        assert r.cum_s[mid] / r.duration_s == pytest.approx(r.cum_mi[mid] / r.length_mi, abs=1e-6)


@respx.mock
async def test_valhalla_asks_for_maneuvers_so_hosted_servers_return_per_stretch_times() -> None:
    route = respx.post(VALHALLA).mock(
        return_value=httpx.Response(200, json=json.loads((FIXTURES / "valhalla_den_slc.json").read_text()))
    )

    await ValhallaRouting(VALHALLA).routes(DENVER, SLC, gross_lb=44_000)

    sent = json.loads(route.calls.last.request.content)
    assert sent["directions_type"] == "maneuvers" and sent["narrative"] is True


@respx.mock
async def test_fewer_than_three_routes_are_topped_up_from_the_second_provider() -> None:
    full = json.loads((FIXTURES / "valhalla_den_slc.json").read_text())
    single = {"trip": full["trip"]}  # e.g. Stadia on a short trip: one route, no alternates
    respx.post("https://primary.test/route").mock(return_value=httpx.Response(200, json=single))
    respx.post(VALHALLA).mock(return_value=httpx.Response(200, json=full))
    routing = FallbackRouting(ValhallaRouting("https://primary.test/route"), ValhallaRouting(VALHALLA))

    routes = await routing.routes(DENVER, SLC, gross_lb=44_000)

    # Primary's route first, then the secondary's; analyze() drops duplicates and keeps three.
    assert len(routes) == 4
    assert routes[0].length_mi == routes[1].length_mi


@respx.mock
async def test_three_routes_from_the_primary_need_no_second_request() -> None:
    respx.post("https://primary.test/route").mock(
        return_value=httpx.Response(200, json=json.loads((FIXTURES / "valhalla_den_slc.json").read_text()))
    )
    secondary = respx.post(VALHALLA).mock(return_value=httpx.Response(503))
    routing = FallbackRouting(ValhallaRouting("https://primary.test/route"), ValhallaRouting(VALHALLA))

    assert len(await routing.routes(DENVER, SLC, gross_lb=44_000)) == 3
    assert not secondary.called


@respx.mock
async def test_a_failed_top_up_keeps_the_primary_routes() -> None:
    full = json.loads((FIXTURES / "valhalla_den_slc.json").read_text())
    respx.post("https://primary.test/route").mock(
        return_value=httpx.Response(200, json={"trip": full["trip"]})
    )
    respx.post(VALHALLA).mock(return_value=httpx.Response(503))
    routing = FallbackRouting(
        ValhallaRouting("https://primary.test/route"), ValhallaRouting(VALHALLA, backoff_s=0)
    )

    assert len(await routing.routes(DENVER, SLC, gross_lb=44_000)) == 1
