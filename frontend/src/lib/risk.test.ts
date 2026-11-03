import { describe, expect, it } from 'vitest'
import { LEVELS, levelInfo, milesBreakdown } from './risk'

describe('levelInfo', () => {
  it('names every level the way the brief does', () => {
    expect(LEVELS.map((l) => levelInfo(l).label)).toEqual(['Low', 'Moderate', 'High', 'Severe', 'No Travel', 'Unknown'])
  })

  it('uses one hue per level, with a neutral grey for missing data', () => {
    expect(levelInfo(3).color).toBe('#F0435A')
    expect(levelInfo(-1).color).toBe('#7E868E')
  })

  it('draws No Travel as barricade red, deeper than Severe', () => {
    expect(levelInfo(4).color).toBe('#D9233F')
    expect(levelInfo(4).color).not.toBe(levelInfo(3).color)
  })
})

describe('milesBreakdown', () => {
  it('lists only the levels a route actually has, worst first, with share of the route', () => {
    const rows = milesBreakdown({ low: 400, moderate: 60, high: 30, severe: 10, no_travel: 0, unknown: 0 })

    expect(rows).toEqual([
      { level: 3, miles: 10, share: 0.02 },
      { level: 2, miles: 30, share: 0.06 },
      { level: 1, miles: 60, share: 0.12 },
      { level: 0, miles: 400, share: 0.8 },
    ])
  })
})
