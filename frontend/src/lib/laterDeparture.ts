import type { HeatPoint, Route } from '../api/types'
import { nearestHeatPoint } from './heat'

const HOUR_MS = 3_600_000
const LAST_HOUR = 48
const NO_TRAVEL = 4

/**
 * The earliest whole-hour delay (1…48) after which the route would meet no No-Travel conditions,
 * estimated from the corridor forecast the response already carries: each checkpoint is read at
 * its nearest corridor point, at the hour the truck would reach it after the delay. Missing data
 * never counts as clear. Returns null when no delay inside the 48 h forecast clears the route.
 *
 * The heat grid is coarser than the checkpoints, so this is an estimate to re-run, not a verdict.
 */
export function earliestClearDeparture(route: Route, heat: HeatPoint[], departureUtc: string): number | null {
  const start = Date.parse(departureUtc)
  const stops: { offsetH: number; point: HeatPoint }[] = []
  for (const cp of route.checkpoints) {
    const point = nearestHeatPoint(heat, cp.lat, cp.lon)
    if (!point) return null
    stops.push({ offsetH: (Date.parse(cp.eta_utc) - start) / HOUR_MS, point })
  }
  if (!stops.length) return null

  for (let delay = 1; delay <= LAST_HOUR; delay++) {
    let clear = true
    for (const { offsetH, point } of stops) {
      const hour = Math.round(delay + offsetH)
      if (hour > LAST_HOUR) return null // the rest of the trip falls outside the forecast
      const level = point.r[hour]
      if (level === NO_TRAVEL || level === -1 || level === undefined) {
        clear = false
        break
      }
    }
    if (clear) return delay
  }
  return null
}
