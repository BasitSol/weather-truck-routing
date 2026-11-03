import { describe, expect, it } from 'vitest'
import type { TripDraft } from './validate'
import { validateTrip } from './validate'

const NOW = new Date('2026-11-03T15:00:00Z')
const good: TripDraft = {
  origin: { label: 'Denver, Colorado, US', lat: 39.7392, lon: -104.9903, tz: 'America/Denver' },
  destination: { label: 'Salt Lake City, Utah, US', lat: 40.7608, lon: -111.891, tz: 'America/Denver' },
  departureWall: '2026-11-04T08:00',
  loadText: '44,000',
  interval: 25,
}

describe('validateTrip', () => {
  it('accepts a complete trip and builds the API request with an offset departure', () => {
    const result = validateTrip(good, NOW)

    expect(result.errors).toEqual({})
    expect(result.request).toEqual({
      origin: { label: 'Denver, Colorado, US', lat: 39.7392, lon: -104.9903 },
      destination: { label: 'Salt Lake City, Utah, US', lat: 40.7608, lon: -111.891 },
      departure_at: '2026-11-04T08:00:00-07:00',
      load_lb: 44000,
      interval: 25,
    })
  })

  it('requires both places to be picked from suggestions', () => {
    const { errors } = validateTrip({ ...good, origin: null, destination: null }, NOW)

    expect(errors.origin).toBe('Choose a starting point from the suggestions.')
    expect(errors.destination).toBe('Choose a destination from the suggestions.')
  })

  it('rejects the same place twice', () => {
    expect(validateTrip({ ...good, destination: good.origin }, NOW).errors.destination).toBe(
      'Destination must be different from the starting point.',
    )
  })

  it('keeps load weight within 1 to 80,000 lb', () => {
    expect(validateTrip({ ...good, loadText: '0' }, NOW).errors.load).toBe('Enter a weight from 1 to 80,000 lb.')
    expect(validateTrip({ ...good, loadText: '90,000' }, NOW).errors.load).toBe('Enter a weight from 1 to 80,000 lb.')
    expect(validateTrip({ ...good, loadText: '' }, NOW).errors.load).toBe('Enter a weight from 1 to 80,000 lb.')
  })

  it('keeps departure inside the forecast window', () => {
    expect(validateTrip({ ...good, departureWall: '2026-11-03T05:00' }, NOW).errors.departure).toBe(
      "Departure can't be in the past.",
    )
    expect(validateTrip({ ...good, departureWall: '2026-11-20T08:00' }, NOW).errors.departure).toBe(
      'Pick a departure within the next 14 days, the range of the forecast.',
    )
  })
})
