// Hand-written from docs/API.md. Keep in sync with backend trips/api/serializers.py.

/** −1 Unknown, 0 Low, 1 Moderate, 2 High, 3 Severe, 4 No Travel */
export type Level = -1 | 0 | 1 | 2 | 3 | 4
export type Interval = 10 | 25 | 50

export interface Place {
  label: string
  lat: number
  lon: number
  /** IANA zone of the place, e.g. "America/Denver" (from /geocode). */
  tz?: string
}

export interface AnalyzeRequest {
  origin: Pick<Place, 'label' | 'lat' | 'lon'>
  destination: Pick<Place, 'label' | 'lat' | 'lon'>
  departure_at: string // ISO-8601 with offset
  load_lb: number
  interval: Interval
}

export interface Weather {
  wind_mph: number
  gust_mph: number | null
  rain_in_hr: number
  snow_in_hr: number
}

export interface Checkpoint {
  idx: number
  mile: number
  lat: number
  lon: number
  tz: string
  eta_utc: string
  eta_local: string
  owned_mi: number
  weather: Weather | null
  levels: Partial<Record<'wind' | 'rain' | 'snow', Level>>
  risk: Level
  driver: string
}

export interface MilesByLevel {
  low: number
  moderate: number
  high: number
  severe: number
  no_travel: number
  unknown: number
}

export interface RouteSummary {
  distance_mi: number
  duration_min: number
  arrive_utc: string
  arrive_local: string
  arrive_tz: string
  avg_risk: number | null
  worst: Level
  miles: MilesByLevel
  checkpoints: number
}

export interface Segment {
  from_mi: number
  to_mi: number
  risk: Level
  coordinates: [number, number][] // [lon, lat]
}

export interface Route {
  id: string
  label: string
  summary: RouteSummary
  segments: Segment[]
  checkpoints: Checkpoint[]
  notices: string[]
}

export type DecidedBy = 'severe_miles' | 'high_miles' | 'avg_risk' | 'duration' | 'only_route' | 'tie'

export interface Recommendation {
  route_id: string
  ranking: string[]
  decided_by: DecidedBy
  reasons: string[]
  warnings: string[]
}

export interface HeatPoint {
  lat: number
  lon: number
  /** One level per hour from departure, hours 0…48 inclusive. */
  r: Level[]
}

export interface AnalyzeResponse {
  meta: {
    request_id: string
    origin: string
    destination: string
    departure_utc: string
    departure_local: string
    origin_tz: string
    interval_mi: Interval
    load_lb: number
    routing_provider: string
    weather_provider: string
    generated_at: string
    timings_ms: Record<string, number>
  }
  routes: Route[]
  recommendation: Recommendation
  heatmap: { start_utc: string; hours: number; points: HeatPoint[] }
}

export interface ApiErrorBody {
  error: { code: string; message: string; fields?: Record<string, string[]> }
}
