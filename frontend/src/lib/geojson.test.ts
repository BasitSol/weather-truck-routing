import { describe, expect, it } from 'vitest'
import type { HeatPoint, Route } from '../api/types'
import { boundsOf, checkpointCollection, heatCollection, routeCollection } from './geojson'

const route = (id: string, coords: [number, number][]): Route => ({
  id,
  label: id,
  summary: {
    distance_mi: 20, duration_min: 30, arrive_utc: '', arrive_local: '', arrive_tz: 'UTC',
    avg_risk: 0, worst: 0, checkpoints: 2,
    miles: { low: 20, moderate: 0, high: 0, severe: 0, no_travel: 0, unknown: 0 },
  },
  segments: [
    { from_mi: 0, to_mi: 10, risk: 0, coordinates: coords.slice(0, 2) },
    { from_mi: 10, to_mi: 20, risk: 3, coordinates: coords.slice(1) },
  ],
  checkpoints: [],
  notices: [],
})

describe('routeCollection', () => {
  it('emits one LineString per risk segment tagged with route and risk', () => {
    const fc = routeCollection([route('r1', [[-105, 39], [-106, 40], [-107, 41]])])

    expect(fc.features).toHaveLength(2)
    expect(fc.features[1].properties).toEqual({ route_id: 'r1', risk: 3, from_mi: 10, to_mi: 20 })
    expect(fc.features[1].geometry.coordinates).toEqual([[-106, 40], [-107, 41]])
  })
})

describe('heatCollection', () => {
  it('flattens hourly levels into r0…rN properties so the map can switch hours with one expression', () => {
    const points: HeatPoint[] = [{ lat: 40, lon: -105, r: [0, 1, 2] }]

    const fc = heatCollection(points)

    expect(fc.features[0].geometry.coordinates).toEqual([-105, 40])
    expect(fc.features[0].properties).toEqual({ r0: 0, r1: 1, r2: 2 })
  })
})

describe('boundsOf', () => {
  it('covers every coordinate of every route', () => {
    expect(boundsOf([route('r1', [[-105, 39], [-106, 40], [-107, 41]])])).toEqual([[-107, 39], [-105, 41]])
  })
})

describe('checkpointCollection', () => {
  it('gives each checkpoint the bearing of the road through it, so reflectors face along the route', () => {
    const r = route('r1', [[-105, 39], [-105, 40], [-104, 40]])
    r.checkpoints = [
      { idx: 0, mile: 0, lat: 39, lon: -105, tz: 'UTC', eta_utc: '', eta_local: '', owned_mi: 5, weather: null, levels: {}, risk: 0, driver: '' },
      { idx: 1, mile: 10, lat: 40, lon: -105, tz: 'UTC', eta_utc: '', eta_local: '', owned_mi: 10, weather: null, levels: {}, risk: 0, driver: '' },
      { idx: 2, mile: 20, lat: 40, lon: -104, tz: 'UTC', eta_utc: '', eta_local: '', owned_mi: 5, weather: null, levels: {}, risk: 0, driver: '' },
    ]

    const bearings = checkpointCollection([r]).features.map((f) => Math.round(f.properties.bearing))

    expect(bearings[0]).toBe(0) // heading north to the next checkpoint
    expect(bearings[2]).toBe(90) // arriving heading east
  })

  it('marks checkpoints at least 20 miles apart as major, so zoomed-out reflectors do not touch', () => {
    const r = route('r1', [[-105, 39], [-105, 40], [-104, 40]])
    r.checkpoints = [0, 10, 20, 30, 40, 45].map((mile, idx) => ({
      idx, mile, lat: 39, lon: -105, tz: 'UTC', eta_utc: '', eta_local: '', owned_mi: 10, weather: null, levels: {}, risk: 0 as const, driver: '',
    }))

    const major = checkpointCollection([r]).features.map((f) => f.properties.major)

    expect(major).toEqual([true, false, true, false, true, false])
  })
})
