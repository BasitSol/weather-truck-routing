import { describe, expect, it } from 'vitest'
import { dayChanges, defaultDepartureWall, formatDuration, formatLocal, hourLabel, tzAbbr, wallTimeToISO } from './time'

describe('wallTimeToISO', () => {
  it('reads the wall time in the given zone and returns an offset ISO string', () => {
    expect(wallTimeToISO('2026-11-03T08:00', 'America/Denver')).toBe('2026-11-03T08:00:00-07:00')
    expect(wallTimeToISO('2026-07-03T08:00', 'America/Denver')).toBe('2026-07-03T08:00:00-06:00')
    expect(wallTimeToISO('2026-11-03T08:00', 'America/New_York')).toBe('2026-11-03T08:00:00-05:00')
  })

  it('handles zones east of UTC and half-hour offsets', () => {
    expect(wallTimeToISO('2026-11-03T08:00', 'Asia/Kolkata')).toBe('2026-11-03T08:00:00+05:30')
    expect(wallTimeToISO('2026-11-03T08:00', 'UTC')).toBe('2026-11-03T08:00:00+00:00')
  })
})

describe('formatLocal', () => {
  it('shows weekday, 24 h time and the zone abbreviation of the place', () => {
    expect(formatLocal('2026-11-03T15:31:00Z', 'America/Denver')).toBe('Tue 08:31 MST')
    expect(formatLocal('2026-11-03T15:31:00Z', 'America/Los_Angeles')).toBe('Tue 07:31 PST')
  })
})

describe('tzAbbr', () => {
  it('names the zone the way a driver reads it', () => {
    expect(tzAbbr('America/Denver', new Date('2026-11-03T15:00:00Z'))).toBe('MST')
    expect(tzAbbr('America/Denver', new Date('2026-07-03T15:00:00Z'))).toBe('MDT')
  })
})

describe('hourLabel', () => {
  it('gives the local time at the origin plus the offset from departure', () => {
    expect(hourLabel('2026-11-03T15:00:00Z', 9, 'America/Denver')).toBe('Tue 17:00 MST, +9 h')
    expect(hourLabel('2026-11-03T15:00:00Z', 0, 'America/Denver')).toBe('Tue 08:00 MST, departure')
    expect(hourLabel('2026-11-03T15:00:00Z', 48, 'America/Denver')).toBe('Thu 08:00 MST, +48 h')
  })
})

describe('formatDuration', () => {
  it('renders minutes as hours and minutes', () => {
    expect(formatDuration(477)).toBe('7 h 57 min')
    expect(formatDuration(45)).toBe('45 min')
    expect(formatDuration(120)).toBe('2 h 0 min')
  })
})

describe('defaultDepartureWall', () => {
  it('is the next full hour plus one, in the given zone', () => {
    const now = new Date('2026-11-03T15:20:00Z') // 08:20 in Denver
    expect(defaultDepartureWall('America/Denver', now)).toBe('2026-11-03T10:00')
  })
})

describe('dayChanges', () => {
  it('marks the first stop and every stop whose local date differs from the one before', () => {
    const stops = [
      { eta_utc: '2026-11-03T19:00:00Z', tz: 'America/Chicago' }, // Tue 13:00
      { eta_utc: '2026-11-04T04:00:00Z', tz: 'America/Chicago' }, // Tue 22:00
      { eta_utc: '2026-11-04T07:00:00Z', tz: 'America/Denver' }, //  Wed 00:00
      { eta_utc: '2026-11-04T08:00:00Z', tz: 'America/Denver' }, //  Wed 01:00
    ]

    expect(dayChanges(stops)).toEqual([true, false, true, false])
  })
})
