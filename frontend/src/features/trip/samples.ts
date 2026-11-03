import type { Interval, Place } from '../../api/types'
import { formatLb } from '../../lib/load'
import { browserTz, defaultDepartureWall } from '../../lib/time'
import type { TripDraft } from './validate'

export interface SampleTrip {
  name: string
  origin: Place
  destination: Place
  loadLb: number
  interval: Interval
}

// Each sample exercises a different part of the brief (docs/API.md "Sample trips").
export const SAMPLE_TRIPS: SampleTrip[] = [
  {
    name: 'Denver to Salt Lake City',
    origin: { label: 'Denver, Colorado, US', lat: 39.7392, lon: -104.9903, tz: 'America/Denver' },
    destination: { label: 'Salt Lake City, Utah, US', lat: 40.7608, lon: -111.891, tz: 'America/Denver' },
    loadLb: 44_000,
    interval: 25,
  },
  {
    name: 'Seattle to Spokane',
    origin: { label: 'Seattle, Washington, US', lat: 47.6062, lon: -122.3321, tz: 'America/Los_Angeles' },
    destination: { label: 'Spokane, Washington, US', lat: 47.6588, lon: -117.426, tz: 'America/Los_Angeles' },
    loadLb: 38_000,
    interval: 10,
  },
  {
    name: 'Dallas to Denver',
    origin: { label: 'Dallas, Texas, US', lat: 32.7767, lon: -96.797, tz: 'America/Chicago' },
    destination: { label: 'Denver, Colorado, US', lat: 39.7392, lon: -104.9903, tz: 'America/Denver' },
    loadLb: 30_000,
    interval: 50,
  },
]

/** The form state a sample trip fills in: departure is the next full hour + 1, at the start city. */
export function sampleDraft(trip: SampleTrip, now: Date = new Date()): TripDraft {
  return {
    origin: trip.origin,
    destination: trip.destination,
    departureWall: defaultDepartureWall(trip.origin.tz ?? browserTz(), now),
    loadText: formatLb(trip.loadLb),
    interval: trip.interval,
  }
}

/** Sample trips as start-to-destination lines for the first-run map. */
export function sampleCollection(): GeoJSON.FeatureCollection<GeoJSON.LineString, { name: string; label: string; load: string }> {
  return {
    type: 'FeatureCollection',
    features: SAMPLE_TRIPS.map((t) => ({
      type: 'Feature' as const,
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [t.origin.lon, t.origin.lat],
          [t.destination.lon, t.destination.lat],
        ],
      },
      properties: { name: t.name, label: `${t.name}, ${formatLb(t.loadLb)} lb`, load: `${formatLb(t.loadLb)} lb` },
    })),
  }
}
