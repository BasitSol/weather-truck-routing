# Architecture

```
Browser (React + TypeScript SPA)                Django + DRF (one container)                    Keyless APIs
┌───────────────────────────────┐   /api/v1   ┌─────────────────────────────────────────┐
│ TripForm  (typeahead, load    │────────────▶│ api/        validation, errors, JSON    │
│            scale, interval)   │             │ services/   analyze() orchestration,    │──▶ Valhalla (truck routes)
│ Verdict · RouteTickets ·      │             │             caching decorators, tz      │──▶ Open-Meteo (hourly forecast)
│ CheckpointTable               │             │ providers/  Valhalla · Open-Meteo ·     │──▶ Photon (place search)
│ MapView   (MapLibre, ref)     │             │             Photon · fakes for tests    │
│ HeatControl (0–48 h slider)   │             │ domain/     pure Python: risk, sampling,│
│ TanStack Query · Zustand      │             │             ETA, weather-at-ETA, miles, │
└───────────────────────────────┘             │             ranking, explanation, heat  │
          tiles ─────────────────────────────▶│ OpenFreeMap (vector basemap)            │
                                              └─────────────────────────────────────────┘
```

## Backend layers

- **`trips/domain`** is the 40% of the grade that is logic. It is pure Python over dataclasses,
  has no Django imports, and type-checks under `mypy --strict`. Every rule in the brief lives here
  and is tested at its boundaries.
- **`trips/providers`** are adapters behind three small protocols (`RoutingProvider`,
  `WeatherProvider`, `GeocodeProvider`). They share one HTTP policy: timeouts, three attempts with
  jittered backoff on 429/5xx/timeouts, and a typed `ProviderError`. Swapping Valhalla for HERE
  means one new class.
- **`trips/services/analyze.py`** runs one analysis:
  1. fetch routes and drop near-duplicate alternates;
  2. place checkpoints, interpolate position and cumulative time, add the local time zone;
  3. collect every checkpoint and corridor point, snap to a 0.05° grid and de-duplicate, so neighbouring routes share forecasts;
  4. fetch the hourly forecast for exactly departure → max(last ETA, departure + 48 h), in parallel chunks;
  5. classify each checkpoint at its ETA, aggregate miles and average risk;
  6. rank, explain and warn;
  7. build 49 hourly levels per corridor point with the same classifier and load rules.
- **Caching** (in-process): routes 10 min, weather per grid cell 30 min, geocode 24 h. Re-running the
  same trip reuses both, so it returns in well under a second. Changing only the load reuses the
  weather; routes are requested again, because the truck's weight is part of the routing request.
- **`trips/api`** validates input, maps errors to one envelope, shapes the response (risk
  segments are sliced from the full-resolution polyline, then simplified), and serves the built SPA.

## Frontend

- **Server state** is TanStack Query (analysis mutation, cached typeahead). **UI state** is a small
  Zustand store: selected route, hovered/open checkpoint, hovered stretch, slider hour.
- **The map instance lives in a ref.** Sources and layers are created once on load. A new analysis
  calls `setData`; selection and hover change paint properties, filters and feature-state; nothing
  is rebuilt.
- **The slider never calls the server and never re-renders the map.** The store hour is read
  through a subscription outside React, and at most one `setPaintProperty` runs per animation frame.
- MapLibre and its web worker are a lazy chunk; the initial bundle is about 95 KB gzipped.

## Deployment

One multi-stage Docker image: Node builds the SPA, Python serves it. WhiteNoise serves the hashed
assets with immutable caching, and a catch-all view returns `index.html` for client routes. Gunicorn
runs threaded workers so concurrent requests overlap their outbound API calls.
