"""Encoded polyline decoding (Google algorithm). Valhalla uses precision 6."""

from __future__ import annotations

from trips.domain.models import LatLon


def decode(encoded: str, precision: int = 6) -> list[LatLon]:
    factor = 10**precision
    points: list[LatLon] = []
    index = lat = lon = 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append(LatLon(lat / factor, lon / factor))
    return points
