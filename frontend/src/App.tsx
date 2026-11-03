import { ArrowClockwise, PencilSimple, RoadHorizon } from '@phosphor-icons/react'
import { type ComponentProps, Suspense, lazy, useEffect, useRef, useState } from 'react'
import { useAnalyze } from './api/client'
import type { AnalyzeRequest, AnalyzeResponse } from './api/types'
import { HeatControl } from './features/heat/HeatControl'
import { Legend } from './features/map/Legend'
import { CheckpointTable } from './features/results/CheckpointTable'
import { RouteTickets } from './features/results/RouteTickets'
import { Verdict } from './features/results/Verdict'
import { TripForm } from './features/trip/TripForm'
import { SAMPLE_TRIPS, sampleDraft } from './features/trip/samples'
import { type TripDraft, validateTrip } from './features/trip/validate'
import { formatLb } from './lib/load'
import { browserTz, formatLocal, nowWall } from './lib/time'
import { useUi } from './store/ui'
import './App.css'

const MapView = lazy(() => import('./features/map/MapView'))

export default function App() {
  const analyze = useAnalyze()
  const [lastRequest, setLastRequest] = useState<AnalyzeRequest | null>(null)
  const [draft, setDraft] = useState<TripDraft | undefined>()
  const [editing, setEditing] = useState(true)
  const [formKey, setFormKey] = useState(0)
  const [data, setData] = useState<AnalyzeResponse | null>(null)

  function run(request: AnalyzeRequest, next?: TripDraft) {
    if (next) setDraft(next)
    setLastRequest(request)
    analyze.mutate(request, {
      onSuccess: (res) => {
        setData(res)
        useUi.getState().reset(res.recommendation.route_id)
        setEditing(false)
      },
      onError: (err) => {
        if (err.code !== 'validation_error') setData(null) // never leave the last trip on screen as if current
      },
    })
  }

  // A sample trip clicked on the first-run map fills the form and runs it, like the panel's list.
  function runSample(name: string) {
    const trip = SAMPLE_TRIPS.find((t) => t.name === name)
    if (!trip || analyze.isPending) return
    const next = sampleDraft(trip)
    const { request } = validateTrip(next, new Date(), browserTz())
    if (!request) return
    setFormKey((k) => k + 1)
    run(request, next)
  }

  // "Do not depart": re-run the same trip leaving later, and keep the form in step with it.
  function recheckLater(delayH: number) {
    if (!lastRequest || !data || analyze.isPending) return
    const at = new Date(Date.parse(data.meta.departure_utc) + delayH * 3_600_000)
    const next = draft ? { ...draft, departureWall: nowWall(data.meta.origin_tz, at) } : undefined
    setFormKey((k) => k + 1)
    run({ ...lastRequest, departure_at: at.toISOString() }, next)
  }

  const error = analyze.error
  const serverFields = error?.code === 'validation_error' ? error.fields : undefined

  return (
    <div className="app">
      <header className="shell">
        <div className="brand">
          <RoadHorizon size={22} weight="bold" aria-hidden />
          <h1>Weather-Aware Truck Routing</h1>
        </div>
        <p className="sources">Truck routes from Valhalla, forecasts from Open-Meteo</p>
      </header>

      <aside className="panel" aria-label="Trip and results">
        {/* Status and failure come first in the panel, where the eye already is, never below the form. */}
        {analyze.isPending && lastRequest && <PendingTrip request={lastRequest} />}

        {error && !analyze.isPending && error.code !== 'validation_error' && (
          <ScrollIntoView className="panel-section error-ticket" role="alert">
            <h2 className="section-title">Couldn't analyze this trip</h2>
            <p>{error.message}</p>
            {lastRequest && (
              <button type="button" className="secondary" onClick={() => run(lastRequest)}>
                <ArrowClockwise size={16} weight="bold" aria-hidden />
                Try again
              </button>
            )}
          </ScrollIntoView>
        )}

        {analyze.isPending ? null : editing || !data ? (
          <section className="panel-section" aria-labelledby="trip-title">
            <h2 id="trip-title" className="panel-title">
              Three truck routes, scored by the weather where the truck will be
            </h2>
            <p className="intro">Each stretch is read at the hour the truck reaches it, for this load.</p>
            <TripForm key={formKey} initial={draft} pending={analyze.isPending} serverErrors={serverFields} onSubmit={run} />
          </section>
        ) : (
          <TripSummary
            data={data}
            onEdit={() => {
              setFormKey((k) => k + 1)
              setEditing(true)
            }}
          />
        )}

        {data && !analyze.isPending && <Results data={data} onRecheck={recheckLater} />}
      </aside>

      <main className="map-area">
        <Suspense fallback={<div className="map-canvas map-loading" aria-hidden />}>
          <MapView data={data} onSample={runSample} />
        </Suspense>
        {analyze.isPending && (
          <p className="map-status" aria-hidden>
            <span className="lane-progress" />
            Finding routes and reading the forecast
          </p>
        )}
        <Legend />
        <HeatControl data={data} />
      </main>
    </div>
  )
}

function TripSummary({ data, onEdit }: { data: AnalyzeResponse; onEdit: () => void }) {
  const m = data.meta
  return (
    <section className="panel-section trip-summary" aria-label="Current trip">
      <div className="summary-head">
        {/* The route block's markers and spine, read-only. */}
        <div className="summary-route">
          <p className="summary-stop">
            <span className="place-marker" data-kind="origin" aria-hidden />
            <span className="visually-hidden">From </span>
            {shortPlace(m.origin)}
          </p>
          <p className="summary-stop">
            <span className="place-marker" data-kind="destination" aria-hidden />
            <span className="visually-hidden">To </span>
            {shortPlace(m.destination)}
          </p>
        </div>
        <button type="button" className="secondary" onClick={onEdit}>
          <PencilSimple size={16} weight="bold" aria-hidden />
          Edit trip
        </button>
      </div>
      <dl className="summary-facts">
        <div>
          <dt>Departs</dt>
          <dd className="figure">{formatLocal(m.departure_utc, m.origin_tz)}</dd>
        </div>
        <div>
          <dt>Load</dt>
          <dd className="figure">{formatLb(m.load_lb)} lb</dd>
        </div>
        <div>
          <dt>Weather every</dt>
          <dd className="figure">{m.interval_mi} mi</dd>
        </div>
      </dl>
    </section>
  )
}

function Results({ data, onRecheck }: { data: AnalyzeResponse; onRecheck: (delayH: number) => void }) {
  const selected = useUi((s) => s.selectedRouteId)
  const route = data.routes.find((r) => r.id === selected) ?? data.routes[0]
  return (
    <>
      <Verdict data={data} onRecheck={onRecheck} />
      <RouteTickets data={data} />
      <CheckpointTable route={route} intervalMi={data.meta.interval_mi} />
    </>
  )
}

/** The trip being analyzed, at the top of the panel, where its result will appear. */
function PendingTrip({ request }: { request: AnalyzeRequest }) {
  return (
    <ScrollIntoView className="panel-section pending" role="status" aria-live="polite">
      <div className="summary-route">
        <p className="summary-stop">
          <span className="place-marker" data-kind="origin" aria-hidden />
          <span className="visually-hidden">From </span>
          {shortPlace(request.origin.label)}
        </p>
        <p className="summary-stop">
          <span className="place-marker" data-kind="destination" aria-hidden />
          <span className="visually-hidden">To </span>
          {shortPlace(request.destination.label)}
        </p>
      </div>
      <span className="lane-progress" aria-hidden />
      <p className="pending-line">
        Finding up to three truck routes, then reading the forecast at each checkpoint for the hour the truck
        gets there.
      </p>
    </ScrollIntoView>
  )
}

/** A panel section that brings itself into view when it appears (status and errors). */
function ScrollIntoView({ children, ...props }: ComponentProps<'section'>) {
  const ref = useRef<HTMLElement>(null)
  useEffect(() => {
    ref.current?.scrollIntoView({ block: 'nearest', behavior: reducedMotion() ? 'auto' : 'smooth' })
  }, [])
  return (
    <section ref={ref} {...props}>
      {children}
    </section>
  )
}

function reducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

function shortPlace(label: string): string {
  return label.split(',').slice(0, 2).join(',')
}
