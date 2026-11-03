"""Place search via Photon (OpenStreetMap, keyless). Typeahead never fails loudly."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from trips.domain.models import LatLon, Place
from trips.providers.base import ProviderError, client, request_json

log = logging.getLogger(__name__)


class PhotonGeocoder:
    name = "photon"

    def __init__(self, url: str, user_agent: str | None = None, backoff_s: float = 0.4) -> None:
        self.url = url
        self.user_agent = user_agent
        self.backoff_s = backoff_s

    async def suggest(self, q: str, at: LatLon | None, limit: int) -> list[Place]:
        params: dict[str, Any] = {"q": q, "limit": limit, "lang": "en"}
        if at is not None:
            params.update(lat=at.lat, lon=at.lon)
        try:
            async with client(self.user_agent) as http:
                payload = await request_json(
                    http,
                    "GET",
                    self.url,
                    provider=self.name,
                    retries=1,
                    backoff_s=self.backoff_s,
                    params=params,
                )
        except (ProviderError, httpx.HTTPError, ValueError) as exc:
            log.warning("geocode failed for %r: %s", q, exc)
            return []

        places: list[Place] = []
        for feature in payload.get("features", []):
            label = _label(feature.get("properties", {}))
            if not label:
                continue
            lon, lat = feature["geometry"]["coordinates"]
            place = Place(label, round(lat, 6), round(lon, 6))
            if place not in places:
                places.append(place)
        return places


def _label(props: dict[str, Any]) -> str:
    street = " ".join(p for p in (props.get("housenumber"), props.get("street")) if p)
    parts = [props.get("name") or street, props.get("city"), props.get("state"), props.get("countrycode")]
    seen: list[str] = []
    for part in parts:
        if part and part not in seen:
            seen.append(part)
    return ", ".join(seen) if props.get("name") or street else ""
