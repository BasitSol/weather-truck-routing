import { describe, expect, it } from 'vitest'
import type { Route } from '../api/types'
import { doNotDepart, formatMi, routeNoticeOnly, routeSummaryLine } from './summary'

const route = (worst: Route['summary']['worst'], segments: Route['segments'], miles: Partial<Route['summary']['miles']>): Route => ({
  id: 'r1',
  label: 'Route A',
  summary: {
    distance_mi: 100, duration_min: 90, arrive_utc: '', arrive_local: '', arrive_tz: 'UTC', avg_risk: 0, worst, checkpoints: 5,
    miles: { low: 0, moderate: 0, high: 0, severe: 0, no_travel: 0, unknown: 0, ...miles },
  },
  segments,
  checkpoints: [],
  notices: [],
})

describe('routeSummaryLine', () => {
  it('says a calm route is low risk the whole way', () => {
    expect(routeSummaryLine(route(0, [{ from_mi: 0, to_mi: 100, risk: 0, coordinates: [] }], { low: 100 }))).toBe(
      'Low risk the whole way.',
    )
  })

  it('names the worst level, how far it runs and where it first appears', () => {
    const segs: Route['segments'] = [
      { from_mi: 0, to_mi: 37.5, risk: 0, coordinates: [] },
      { from_mi: 37.5, to_mi: 62.5, risk: 3, coordinates: [] },
      { from_mi: 62.5, to_mi: 100, risk: 1, coordinates: [] },
    ]
    expect(routeSummaryLine(route(3, segs, { low: 37.5, severe: 25, moderate: 37.5 }))).toBe(
      'Severe for 25 mi, first around mile 38.',
    )
  })

  it('says so when a route has no forecast at all', () => {
    expect(routeSummaryLine(route(-1, [{ from_mi: 0, to_mi: 100, risk: -1, coordinates: [] }], { unknown: 100 }))).toBe(
      'No forecast for this route.',
    )
  })
})

describe('formatMi', () => {
  it('writes miles at the 0.1 mi the ranking compares, dropping a trailing .0', () => {
    expect(formatMi(90)).toBe('90 mi')
    expect(formatMi(25.24)).toBe('25.2 mi')
    expect(formatMi(1234.56)).toBe('1,234.6 mi')
  })
})

describe('doNotDepart', () => {
  it('is true only when the API leads its warnings with "Do not depart"', () => {
    const rec = (warnings: string[]) => ({ route_id: 'r1', ranking: ['r1'], decided_by: 'only_route' as const, reasons: [], warnings })
    expect(doNotDepart(rec(['Do not depart: the recommended route still crosses 90 mi of No-Travel conditions.']))).toBe(true)
    expect(doNotDepart(rec(['Route B crosses 90 mi of No-Travel conditions.']))).toBe(false)
    expect(doNotDepart(rec([]))).toBe(false)
  })
})

describe('routeNoticeOnly', () => {
  it('drops per-route No-Travel warnings, which each route row already states', () => {
    expect(routeNoticeOnly('Route B crosses 90 mi of No-Travel conditions.')).toBe(false)
    expect(routeNoticeOnly('2 checkpoints on Route C have no forecast data. They are shown as Unknown and counted as High when ranking.')).toBe(true)
  })
})
