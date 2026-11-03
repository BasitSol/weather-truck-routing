# API

Base path `/api/v1`. JSON in and out; responses are gzip-encoded when the client accepts it.
Distances are miles, durations minutes, weights lb, times ISO-8601. `frontend/src/api/types.ts`
mirrors this document.

| Method | Path | Purpose | Throttle |
|---|---|---|---|
| `POST` | `/analyze` | Full trip analysis | 30/min per IP |
| `GET` | `/geocode?q=&at=&limit=` | Place suggestions | 120/min per IP |
| `GET` | `/health` | Liveness | none |

## `POST /analyze`

```json
{
  "origin":      { "label": "Denver, Colorado, US",     "lat": 39.7392, "lon": -104.9903 },
  "destination": { "label": "Salt Lake City, Utah, US", "lat": 40.7608, "lon": -111.891 },
  "departure_at": "2026-11-03T08:00:00-07:00",
  "load_lb": 44000,
  "interval": 25
}
```

| Field | Rules |
|---|---|
| `origin`, `destination` | label 1–200 chars; lat in [−90, 90]; lon in [−180, 180]; more than 0.5 mi apart |
| `departure_at` | ISO-8601 **with a UTC offset**; within [now − 1 h, now + 14 days] |
| `load_lb` | integer, 1 to 80,000 |
| `interval` | 10, 25 or 50 (default 25) |

Response (abridged):

```jsonc
{
  "meta": {
    "request_id": "8bca7389b15e", "origin": "Denver, Colorado, US", "destination": "Salt Lake City, Utah, US",
    "departure_utc": "2026-11-03T15:00:00Z", "departure_local": "2026-11-03T08:00:00-07:00",
    "origin_tz": "America/Denver", "interval_mi": 25, "load_lb": 44000,
    "routing_provider": "valhalla", "weather_provider": "open-meteo",
    "generated_at": "…", "timings_ms": { "route": 1546, "weather": 1245, "compute": 69, "total": 2860 }
  },
  "routes": [{
    "id": "r1", "label": "Route A",
    "summary": {
      "distance_mi": 538.48, "duration_min": 477,
      "arrive_utc": "…", "arrive_local": "…", "arrive_tz": "America/Denver",
      "avg_risk": 0.13, "worst": 1, "checkpoints": 23,   // distance-weighted; no-forecast miles count as High
      "miles": { "low": 463.5, "moderate": 75.0, "high": 0, "severe": 0, "no_travel": 0, "unknown": 0 }
    },
    "segments": [                         // contiguous risk stretches covering [0, distance_mi]
      { "from_mi": 0, "to_mi": 12.5, "risk": 0, "coordinates": [[-104.99, 39.74], …] }   // [lon, lat]
    ],
    "checkpoints": [{
      "idx": 1, "mile": 25, "lat": 39.91, "lon": -105.09, "tz": "America/Denver",
      "eta_utc": "…", "eta_local": "2026-11-03T08:22:00-07:00", "owned_mi": 25,
      "weather": { "wind_mph": 41.3, "gust_mph": 52.0, "rain_in_hr": 0.0, "snow_in_hr": 0.0 },  // null = no forecast; gust may be null
      "levels": { "wind": 2, "rain": 0, "snow": 0 },        // before the load rule; {} when unknown
      "risk": 3,
      "driver": "Wind 41.3 mph with 44,000 lb load (> 40,000 lb) → Severe"
    }],
    "notices": []
  }],
  "recommendation": {
    "route_id": "r2", "ranking": ["r2", "r3", "r1"],
    "decided_by": "severe_miles",         // severe_miles | high_miles | avg_risk | duration | only_route | tie
    "reasons": ["Route B has the fewest Severe miles: 0 mi (Route C: 10 mi, Route A: 20 mi).",
                "+24 min vs the fastest route, Route A, which has more Severe miles (20 mi vs 0 mi)."],
    "warnings": []
  },
  "heatmap": {
    "start_utc": "2026-11-03T15:00:00Z",  // = departure; hour 0
    "hours": 48,
    "points": [{ "lat": 39.75, "lon": -105.0, "r": [0, 0, 1, …] }]   // hours + 1 levels: hour 0 … hour 48
  }
}
```

Levels: −1 Unknown, 0 Low, 1 Moderate, 2 High, 3 Severe, 4 No Travel.

Invariants (asserted in `trips/tests/contract/test_analyze_api.py`): 1 to 3 routes labelled
Route A/B/C in API order; `ranking` lists every route once and starts with `route_id`; segments are
contiguous from 0 to `distance_mi`; the first checkpoint is at mile 0 and the last at
`distance_mi`; owned miles and `miles.*` each sum to `distance_mi`; ETAs never decrease; every
heat series has `hours + 1` values in {−1 … 4}.

### Errors

Every non-2xx response: `{ "error": { "code": "…", "message": "…", "fields": { "load_lb": ["…"] } } }`

| Status | code | When |
|---|---|---|
| 400 | `validation_error` | Invalid input (`fields` names each field) |
| 404 | `no_route` | The routing engine has no truck route between the places, or the trip exceeds its distance limit (the message says which) |
| 429 | `throttled` | Rate limit (`Retry-After` set) |
| 502 | `routing_unavailable` | Routing failed after retries |
| 502 | `weather_unavailable` | **Every** weather request failed. A partial failure is a 200 with Unknown checkpoints and a warning. |
| 503 | `weather_busy` | The weather service refused requests for rate limiting. Nothing is scored on partial data; try again in a minute. |
| 503 | `routing_busy` | The routing service refused requests for rate limiting; try again in a minute. |
| 500 | `internal_error` | Anything else; the message carries a request id |

## `GET /geocode`

`q` 2–100 chars; optional `at=lat,lon` bias; `limit` 1–10 (default 6).

```json
{ "results": [{ "label": "Salt Lake City, Utah, US", "lat": 40.7608, "lon": -111.891, "tz": "America/Denver" }] }
```

Returns `[]` when the provider fails; typeahead never errors.

## Upstream calls

- **Valhalla** `POST {VALHALLA_URL}` with `costing: "truck"`, `costing_options.truck.weight` (metric tons),
  `alternates: 2`, `directions_type: "maneuvers"`. Shapes are polyline6.
- **Open-Meteo** `GET /v1/forecast?latitude=…&longitude=…&hourly=wind_speed_10m,wind_gusts_10m,rain,showers,snowfall&wind_speed_unit=mph&precipitation_unit=inch&timezone=GMT&start_hour=…&end_hour=…`,
  up to 100 grid cells per request, 4 requests in parallel. A single location returns an object, several return a list.
- **Photon** `GET {PHOTON_URL}?q=…&limit=…&lat=…&lon=…`.
