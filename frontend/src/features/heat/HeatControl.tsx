import { useMemo } from 'react'
import type { AnalyzeResponse, HeatPoint, Route } from '../../api/types'
import { LevelIcon } from '../../components/LevelIcon'
import { type HourSummary, corridorTimeline, firstMileAtLevel } from '../../lib/heat'
import { levelInfo } from '../../lib/risk'
import { hourLabel } from '../../lib/time'
import { useUi } from '../../store/ui'

const TICKS = [0, 6, 12, 18, 24, 30, 36, 42, 48]

/**
 * 0–48 h forecast slider for the corridor heat. Every hour is already in the analysis, so moving
 * it never calls the server; only this control re-renders, and the map repaints once per frame.
 */
export function HeatControl({ data }: { data: AnalyzeResponse | null }) {
  const hour = useUi((s) => s.hour)
  const setHour = useUi((s) => s.setHour)
  const selectedId = useUi((s) => s.selectedRouteId)
  const timeline = useMemo(() => corridorTimeline(data?.heatmap.points ?? []), [data])

  if (!data) {
    // The real control, shown inert, so the first screen already says what it will do.
    return (
      <section className="heat-control heat-control-idle" aria-label="Corridor forecast">
        <div className="heat-row">
          <p className="heat-title">Corridor forecast</p>
          <p className="heat-time">0 to 48 h after departure</p>
        </div>
        <div className="heat-slider">
          <input type="range" min={0} max={48} value={0} disabled aria-label="Corridor forecast hour (available after analysis)" />
          <div className="heat-ticks figure" aria-hidden>
            {TICKS.map((t) => (
              <span key={t} style={{ left: `${(t / 48) * 100}%` }} data-departure={t === 0}>
                {t === 0 ? 'Depart' : `+${t}`}
              </span>
            ))}
          </div>
        </div>
        <p className="heat-hint">Run a trip to scrub its weather hour by hour. Click a dashed sample trip on the map to start.</p>
      </section>
    )
  }

  const hours = data.heatmap.hours
  const label = hourLabel(data.heatmap.start_utc, hour, data.meta.origin_tz)
  const route = data.routes.find((r) => r.id === selectedId) ?? data.routes[0]
  const now = timeline[hour]
  const readout = now ? readoutText(now, route, data.heatmap.points, hour) : ''

  return (
    <section className="heat-control" aria-label="Corridor forecast">
      <div className="heat-row">
        <label className="heat-title" htmlFor="heat-hour">
          Corridor forecast
        </label>
        <output className="heat-time figure" htmlFor="heat-hour" aria-live="off">
          {label}
        </output>
      </div>
      <div className="heat-slider">
        {/* The 48 hours at a glance: each cell is the worst level anywhere in the corridor that hour. */}
        <div className="heat-strip" aria-hidden>
          {timeline.map((t, h) => (
            <span key={h} data-level={t.worst} style={{ background: t.worst === 0 ? undefined : levelInfo(t.worst).color }} />
          ))}
        </div>
        <input
          id="heat-hour"
          type="range"
          min={0}
          max={hours}
          step={1}
          value={hour}
          aria-valuetext={readout ? `${label}. ${readout}` : label}
          onChange={(e) => setHour(Number(e.target.value))}
        />
        <div className="heat-ticks figure" aria-hidden>
          {TICKS.filter((t) => t <= hours).map((t) => (
            <span key={t} style={{ left: `${(t / hours) * 100}%` }} data-departure={t === 0}>
              {t === 0 ? 'Depart' : `+${t}`}
            </span>
          ))}
        </div>
      </div>
      {now && (
        <p className="heat-readout">
          <LevelIcon level={now.worst} size={15} />
          <span>{readout}</span>
        </p>
      )}
      <p className="heat-hint">
        Shaded corridor: risk at this hour for this load. Route lines and checkpoints use the time the truck arrives.
      </p>
    </section>
  )
}

/** What the corridor looks like at the slider hour, in words, and where it starts on the selected route. */
function readoutText(now: HourSummary, route: Route, points: HeatPoint[], hour: number): string {
  if (now.worst === 0) return 'Low along the whole corridor.'
  if (now.worst === -1) return 'No forecast for the corridor at this hour.'
  const pct = Math.round(now.share * 100)
  const mile = firstMileAtLevel(route, points, hour, now.worst)
  return (
    `${levelInfo(now.worst).label} on ${pct < 1 ? 'under 1' : pct}% of the corridor` +
    (mile === null ? '.' : `, on ${route.label} from about mile ${Math.round(mile)}.`)
  )
}
