import type { HeatPoint, Level, Route } from '../api/types'

/** Corridor points are ~10 mi apart along every route, so each checkpoint has one within ~0.1°. */
const NEAREST_MAX_DEG = 0.2

export interface HourSummary {
  /** Worst known level anywhere in the corridor; Unknown only when no point has a forecast. */
  worst: Level
  /** Share of corridor points at that level, 0…1. */
  share: number
}

/** One entry per forecast hour: the worst level in the corridor and how much of it is at that level. */
export function corridorTimeline(points: HeatPoint[]): HourSummary[] {
  if (!points.length) return []
  const hours = points[0].r.length
  const out: HourSummary[] = []
  for (let h = 0; h < hours; h++) {
    let worst: Level = -1
    for (const p of points) if (p.r[h] > worst) worst = p.r[h]
    const at = points.filter((p) => p.r[h] === worst).length
    out.push({ worst, share: Math.round((at / points.length) * 100) / 100 })
  }
  return out
}

/** The corridor point closest to a place, or null when none is within reach. */
export function nearestHeatPoint(points: HeatPoint[], lat: number, lon: number): HeatPoint | null {
  const kx = Math.cos((lat * Math.PI) / 180) // degrees of longitude shrink with latitude
  let best: HeatPoint | null = null
  let bestD = NEAREST_MAX_DEG ** 2
  for (const p of points) {
    const d = (p.lat - lat) ** 2 + ((p.lon - lon) * kx) ** 2
    if (d <= bestD) {
      best = p
      bestD = d
    }
  }
  return best
}

/** Mile of the first checkpoint on `route` whose nearest corridor point is at `level` in `hour`. */
export function firstMileAtLevel(route: Route, points: HeatPoint[], hour: number, level: Level): number | null {
  for (const cp of route.checkpoints) {
    if (nearestHeatPoint(points, cp.lat, cp.lon)?.r[hour] === level) return cp.mile
  }
  return null
}
