import { describe, expect, it } from 'vitest'
import { SAMPLE_TRIPS, sampleCollection, sampleDraft } from './samples'
import { validateTrip } from './validate'

describe('sampleDraft', () => {
  it('fills the form with the trip and departs in the start city time zone', () => {
    const now = new Date('2026-11-03T15:20:00Z')
    const dallas = SAMPLE_TRIPS.find((t) => t.name === 'Dallas to Denver')!

    const draft = sampleDraft(dallas, now)
    const { request, errors } = validateTrip(draft, now)

    expect(errors).toEqual({})
    expect(request?.departure_at).toBe('2026-11-03T11:00:00-06:00') // 09:20 CST → next hour + 1
    expect(request?.load_lb).toBe(30_000)
    expect(request?.interval).toBe(50)
  })
})

describe('sampleCollection', () => {
  it('draws each sample as a line from start to destination, named so a click can run it', () => {
    const fc = sampleCollection()

    expect(fc.features).toHaveLength(SAMPLE_TRIPS.length)
    expect(fc.features[0].properties.name).toBe('Denver to Salt Lake City')
    expect(fc.features[0].geometry.coordinates).toEqual([
      [-104.9903, 39.7392],
      [-111.891, 40.7608],
    ])
  })
})
