// Mirrors the API's validation (backend trips/api/serializers.py) so a bad trip never leaves the form.

import type { AnalyzeRequest, Interval, Place } from '../../api/types'
import { MAX_LOAD_LB, parseLb } from '../../lib/load'
import { browserTz, defaultDepartureWall, wallTimeToISO } from '../../lib/time'

export interface TripDraft {
  origin: Place | null
  destination: Place | null
  departureWall: string // "YYYY-MM-DDTHH:mm" in the origin's zone
  loadText: string
  interval: Interval
}

export type TripErrors = Partial<Record<'origin' | 'destination' | 'departure' | 'load', string>>

const HOUR_MS = 3_600_000
const DAY_MS = 24 * HOUR_MS

export function departureZone(draft: Pick<TripDraft, 'origin'>, fallback: string): string {
  return draft.origin?.tz ?? fallback
}

export function validateTrip(
  draft: TripDraft,
  now: Date = new Date(),
  fallbackTz = 'UTC',
): { errors: TripErrors; request: AnalyzeRequest | null } {
  const errors: TripErrors = {}
  const { origin, destination } = draft

  if (!origin) errors.origin = 'Choose a starting point from the suggestions.'
  if (!destination) errors.destination = 'Choose a destination from the suggestions.'
  else if (origin && Math.abs(origin.lat - destination.lat) < 0.005 && Math.abs(origin.lon - destination.lon) < 0.005)
    errors.destination = 'Destination must be different from the starting point.'

  const load = parseLb(draft.loadText)
  if (load === null || load < 1 || load > MAX_LOAD_LB) errors.load = 'Enter a weight from 1 to 80,000 lb.'

  let departureIso = ''
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(draft.departureWall)) {
    errors.departure = 'Enter a departure date and time.'
  } else {
    departureIso = wallTimeToISO(draft.departureWall, departureZone(draft, fallbackTz))
    const t = new Date(departureIso).getTime()
    if (t < now.getTime() - HOUR_MS) errors.departure = "Departure can't be in the past."
    else if (t > now.getTime() + 14 * DAY_MS)
      errors.departure = 'Pick a departure within the next 14 days, the range of the forecast.'
  }

  if (Object.keys(errors).length || !origin || !destination || load === null) return { errors, request: null }
  return {
    errors,
    request: {
      origin: { label: origin.label, lat: origin.lat, lon: origin.lon },
      destination: { label: destination.label, lat: destination.lat, lon: destination.lon },
      departure_at: departureIso,
      load_lb: load,
      interval: draft.interval,
    },
  }
}

export function initialDraft(tz: string = browserTz()): TripDraft {
  return { origin: null, destination: null, departureWall: defaultDepartureWall(tz), loadText: '44,000', interval: 25 }
}
