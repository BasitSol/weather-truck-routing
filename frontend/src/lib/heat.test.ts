import { describe, expect, it } from 'vitest'
import type { Checkpoint, HeatPoint, Level, Route } from '../api/types'
import { corridorTimeline, firstMileAtLevel, nearestHeatPoint } from './heat'

const pt = (lon: number, r: Level[]): HeatPoint => ({ lat: 40, lon, r })

describe('corridorTimeline', () => {
  it('gives each hour the worst level in the corridor and the share of points at it', () => {
    const points = [pt(-105, [0, 1, 3]), pt(-104, [0, 3, 3]), pt(-103, [0, 0, 1]), pt(-102, [0, 0, -1])]

    expect(corridorTimeline(points)).toEqual([
      { worst: 0, share: 1 },
      { worst: 3, share: 0.25 },
      { worst: 3, share: 0.5 },
    ])
  })

  it('never lets a missing forecast hide a known risk, and says Unknown only when nothing is known', () => {
    expect(corridorTimeline([pt(-105, [-1, -1]), pt(-104, [-1, 0])])).toEqual([
      { worst: -1, share: 1 },
      { worst: 0, share: 0.5 },
    ])
  })

  it('is empty without points', () => {
    expect(corridorTimeline([])).toEqual([])
  })
})

describe('nearestHeatPoint', () => {
  it('finds the closest corridor point within reach, and none when too far', () => {
    const points = [pt(-105, [0]), pt(-104.9, [1])]
    expect(nearestHeatPoint(points, 40, -104.92)).toBe(points[1])
    expect(nearestHeatPoint(points, 40, -100)).toBeNull()
  })
})

describe('firstMileAtLevel', () => {
  const cp = (idx: number, mile: number, lon: number): Checkpoint => ({
    idx, mile, lat: 40, lon, tz: 'UTC', eta_utc: '', eta_local: '', owned_mi: 10, weather: null, levels: {}, risk: 0, driver: '',
  })
  const route = { checkpoints: [cp(0, 0, -105), cp(1, 25, -104), cp(2, 50, -103)] } as Route

  it('names the first checkpoint mile whose corridor point is at that level in that hour', () => {
    const points = [pt(-105, [0, 0]), pt(-104, [0, 3]), pt(-103, [3, 3])]
    expect(firstMileAtLevel(route, points, 0, 3)).toBe(50)
    expect(firstMileAtLevel(route, points, 1, 3)).toBe(25)
    expect(firstMileAtLevel(route, points, 1, 4)).toBeNull()
  })
})
