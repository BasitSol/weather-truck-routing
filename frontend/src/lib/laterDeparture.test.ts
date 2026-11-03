import { describe, expect, it } from 'vitest'
import type { Checkpoint, HeatPoint, Level, Route } from '../api/types'
import { earliestClearDeparture } from './laterDeparture'

const DEP = '2026-11-03T15:00:00Z'
const at = (h: number) => new Date(Date.parse(DEP) + h * 3_600_000).toISOString()

const cp = (idx: number, lon: number, etaH: number): Checkpoint => ({
  idx, mile: idx * 25, lat: 40, lon, tz: 'UTC', eta_utc: at(etaH), eta_local: '', owned_mi: 25,
  weather: null, levels: {}, risk: 0, driver: '',
})

const route = (checkpoints: Checkpoint[]): Route => ({
  id: 'r1', label: 'Route A', segments: [], notices: [], checkpoints,
  summary: {
    distance_mi: 50, duration_min: 120, arrive_utc: '', arrive_local: '', arrive_tz: 'UTC', avg_risk: 0, worst: 4,
    checkpoints: checkpoints.length, miles: { low: 0, moderate: 0, high: 0, severe: 0, no_travel: 50, unknown: 0 },
  },
})

/** A heat point whose level is `nt` (No Travel) up to and including `untilHour`, then Low. */
const point = (lon: number, untilHour: number, after: Level = 0): HeatPoint => ({
  lat: 40, lon, r: Array.from({ length: 49 }, (_, h) => (h <= untilHour ? 4 : after) as Level),
})

describe('earliestClearDeparture', () => {
  it('finds the first later departure at which no checkpoint would meet No-Travel conditions', () => {
    // Checkpoints reached 0 h and 2 h after departure; No Travel at the first until hour 5, the second until hour 3.
    const r = route([cp(0, -105, 0), cp(1, -104, 2)])
    const heat = [point(-105, 5), point(-104, 3)]

    // Leaving +6 h: first checkpoint at hour 6 (clear), second at hour 8 (clear).
    expect(earliestClearDeparture(r, heat, DEP)).toBe(6)
  })

  it('reads each checkpoint at the hour the truck would reach it after the delay', () => {
    // The second checkpoint is still No Travel until hour 9, and the truck reaches it 2 h after leaving.
    const r = route([cp(0, -105, 0), cp(1, -104, 2)])
    const heat = [point(-105, 1), point(-104, 9)]

    expect(earliestClearDeparture(r, heat, DEP)).toBe(8)
  })

  it('gives up when the trip would run past the 48 h forecast before clearing', () => {
    const r = route([cp(0, -105, 0), cp(1, -104, 2)])
    const heat = [point(-105, 47), point(-104, 0)]

    expect(earliestClearDeparture(r, heat, DEP)).toBeNull()
  })

  it('does not call a missing forecast clear', () => {
    const r = route([cp(0, -105, 0)])
    const heat = [point(-105, 3, -1)] // after hour 3 the cell has no data

    expect(earliestClearDeparture(r, heat, DEP)).toBeNull()
  })

  it('gives up when a checkpoint has no corridor point nearby', () => {
    const r = route([cp(0, -105, 0)])

    expect(earliestClearDeparture(r, [point(-99, 0)], DEP)).toBeNull()
  })
})
