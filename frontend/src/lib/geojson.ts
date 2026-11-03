import type { Checkpoint, HeatPoint, Level, Route } from '../api/types'

type Position = [number, number]

export interface SegmentProps {
  route_id: string
  risk: Level
  from_mi: number
  to_mi: number
}

export interface CheckpointProps {
  route_id: string
  idx: number
  risk: Level
  /** Compass bearing of the road through the checkpoint, so a reflector can face along it. */
  bearing: number
  /** Kept when zoomed out: the first checkpoint, then each one at least MAJOR_SPACING_MI past the last kept. */
  major: boolean
}

const MAJOR_SPACING_MI = 20

function majorFlags(checkpoints: Pick<Checkpoint, 'mile'>[]): boolean[] {
  let last = -Infinity
  return checkpoints.map((cp) => {
    if (cp.mile - last < MAJOR_SPACING_MI) return false
    last = cp.mile
    return true
  })
}

/** Initial great-circle bearing from a to b, in degrees clockwise from north. */
function bearing(a: Pick<Checkpoint, 'lat' | 'lon'>, b: Pick<Checkpoint, 'lat' | 'lon'>): number {
  const rad = Math.PI / 180
  const dLon = (b.lon - a.lon) * rad
  const y = Math.sin(dLon) * Math.cos(b.lat * rad)
  const x = Math.cos(a.lat * rad) * Math.sin(b.lat * rad) - Math.sin(a.lat * rad) * Math.cos(b.lat * rad) * Math.cos(dLon)
  return ((Math.atan2(y, x) / rad) + 360) % 360
}

export function routeCollection(routes: Route[]): GeoJSON.FeatureCollection<GeoJSON.LineString, SegmentProps> {
  return {
    type: 'FeatureCollection',
    features: routes.flatMap((r) =>
      r.segments.map((s) => ({
        type: 'Feature' as const,
        geometry: { type: 'LineString' as const, coordinates: s.coordinates },
        properties: { route_id: r.id, risk: s.risk, from_mi: s.from_mi, to_mi: s.to_mi },
      })),
    ),
  }
}

/** Stable numeric id per checkpoint so the map can use feature-state for hover. */
export function checkpointFeatureId(routeIndex: number, cp: Pick<Checkpoint, 'idx'>): number {
  return routeIndex * 10_000 + cp.idx
}

export function checkpointCollection(routes: Route[]): GeoJSON.FeatureCollection<GeoJSON.Point, CheckpointProps> {
  return {
    type: 'FeatureCollection',
    features: routes.flatMap((r, i) => {
      const major = majorFlags(r.checkpoints)
      return r.checkpoints.map((cp, k, all) => ({
        type: 'Feature' as const,
        id: checkpointFeatureId(i, cp),
        geometry: { type: 'Point' as const, coordinates: [cp.lon, cp.lat] },
        properties: {
          route_id: r.id,
          idx: cp.idx,
          risk: cp.risk,
          bearing: all.length > 1 ? bearing(all[Math.max(k - 1, 0)], all[Math.min(k + 1, all.length - 1)]) : 0,
          major: major[k],
        },
      }))
    }),
  }
}

/** Hourly levels flattened to r0…rN so one paint expression can switch the visible hour. */
export function heatCollection(points: HeatPoint[]): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: 'FeatureCollection',
    features: points.map((p) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
      properties: Object.fromEntries(p.r.map((level, h) => [`r${h}`, level])),
    })),
  }
}

export function boundsOf(routes: Route[]): [Position, Position] {
  let minLon = Infinity
  let minLat = Infinity
  let maxLon = -Infinity
  let maxLat = -Infinity
  for (const r of routes) {
    for (const s of r.segments) {
      for (const [lon, lat] of s.coordinates) {
        minLon = Math.min(minLon, lon)
        maxLon = Math.max(maxLon, lon)
        minLat = Math.min(minLat, lat)
        maxLat = Math.max(maxLat, lat)
      }
    }
  }
  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ]
}
