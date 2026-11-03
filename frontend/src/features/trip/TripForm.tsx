import { ArrowRight, ArrowsDownUp } from '@phosphor-icons/react'
import { useState } from 'react'
import type { AnalyzeRequest, Interval } from '../../api/types'
import { formatLb } from '../../lib/load'
import { browserTz, nowWall, tzAbbr, wallTimeToISO } from '../../lib/time'
import { LoadScale } from './LoadScale'
import { PlaceInput } from './PlaceInput'
import { SAMPLE_TRIPS, type SampleTrip, sampleDraft } from './samples'
import { type TripDraft, type TripErrors, departureZone, initialDraft, validateTrip } from './validate'

const INTERVALS: Interval[] = [10, 25, 50]

interface Props {
  pending: boolean
  serverErrors?: Record<string, string[]>
  onSubmit: (request: AnalyzeRequest, draft: TripDraft) => void
  initial?: TripDraft
}


export function TripForm({ pending, serverErrors, onSubmit, initial }: Props) {
  const [draft, setDraft] = useState<TripDraft>(() => initial ?? initialDraft())
  const [errors, setErrors] = useState<TripErrors>({})
  const [now] = useState(() => new Date())
  const zone = departureZone(draft, browserTz())
  const zoneNote = draft.origin
    ? `${tzAbbr(zone, new Date(wallTimeToISO(draft.departureWall || nowWall(zone, now), zone)))}, local time at the start`
    : `${tzAbbr(zone, now)}, your time zone until a start is chosen`

  const update = (patch: Partial<TripDraft>) => setDraft((d) => ({ ...d, ...patch }))

  function submit(next: TripDraft) {
    const result = validateTrip(next, new Date(), browserTz())
    setErrors(result.errors)
    if (result.request) onSubmit(result.request, next)
  }

  function runSample(trip: SampleTrip) {
    const next = sampleDraft(trip)
    setDraft(next)
    submit(next)
  }

  const fieldError = (key: keyof TripErrors, server: string) => errors[key] ?? serverErrors?.[server]?.[0]

  return (
    <form
      className="trip-form"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        submit(draft)
      }}
    >
      {/* One ruled block, wearing the map's own Start and Destination markers on a dashed spine. */}
      <div className="route-block">
        <PlaceInput
          label="From"
          role="origin"
          value={draft.origin}
          bias={draft.destination}
          onChange={(origin) => update({ origin })}
          error={fieldError('origin', 'origin')}
        />
        <button
          type="button"
          className="swap"
          aria-label="Swap start and destination"
          title="Swap start and destination"
          onClick={() => update({ origin: draft.destination, destination: draft.origin })}
        >
          <ArrowsDownUp size={16} weight="bold" aria-hidden />
        </button>
        <PlaceInput
          label="To"
          role="destination"
          value={draft.destination}
          bias={draft.origin}
          onChange={(destination) => update({ destination })}
          error={fieldError('destination', 'destination')}
        />
      </div>

      <div className="when">
      <div className="field">
        <label className="field-label" htmlFor="departure">
          Departure
        </label>
        <input
          id="departure"
          type="datetime-local"
          className="text-input figure"
          value={draft.departureWall}
          min={nowWall(zone, now)}
          aria-describedby="departure-zone"
          aria-invalid={Boolean(fieldError('departure', 'departure_at'))}
          onChange={(e) => update({ departureWall: e.target.value })}
        />
        <p id="departure-zone" className="field-help">
          {zoneNote}
        </p>
        {fieldError('departure', 'departure_at') && <p className="field-error">{fieldError('departure', 'departure_at')}</p>}
      </div>

      <fieldset className="field">
        <legend className="field-label">Weather every (mi)</legend>
        <div className="segmented" role="radiogroup">
          {INTERVALS.map((n) => (
            <label key={n} className="segment">
              <input
                type="radio"
                name="interval"
                value={n}
                checked={draft.interval === n}
                onChange={() => update({ interval: n })}
              />
              <span className="tnum">{n}</span>
              <span className="visually-hidden"> miles</span>
            </label>
          ))}
        </div>
      </fieldset>
      </div>

      <LoadScale text={draft.loadText} onChange={(loadText) => update({ loadText })} error={fieldError('load', 'load_lb')} />

      <button type="submit" className="primary" disabled={pending}>
        {pending ? 'Analyzing routes…' : 'Analyze routes'}
      </button>

      <div className="samples">
        <p className="samples-title">Or run a sample trip</p>
        <ul>
          {SAMPLE_TRIPS.map((trip) => (
            <li key={trip.name}>
              <button
                type="button"
                className="sample"
                disabled={pending}
                aria-label={`${trip.name}, ${formatLb(trip.loadLb)} lb, weather every ${trip.interval} mi`}
                onClick={() => runSample(trip)}
              >
                <span className="sample-route" aria-hidden>
                  {trip.name.split(' to ')[0]}
                  <ArrowRight size={14} weight="bold" />
                  {trip.name.split(' to ')[1]}
                </span>
                <span className="sample-meta figure" aria-hidden>
                  {formatLb(trip.loadLb)} lb, {trip.interval} mi
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </form>
  )
}
