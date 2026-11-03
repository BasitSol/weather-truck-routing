import type { AnalyzeResponse, DecidedBy, Route } from '../../api/types'
import { doNotDepart } from '../../lib/summary'
import { useUi } from '../../store/ui'
import { LineDiagram } from './LineDiagram'

// The brief's ranking criteria, in ranking order. Travel time breaks a full risk tie; the tickets show it.
const COLUMNS: { key: DecidedBy; caption: string; value: (r: Route) => string }[] = [
  { key: 'severe_miles', caption: 'Severe+', value: (r) => miles(r.summary.miles.severe + r.summary.miles.no_travel) },
  { key: 'high_miles', caption: 'High+', value: (r) => miles(r.summary.miles.high + r.summary.miles.unknown) },
  { key: 'avg_risk', caption: 'Avg', value: (r) => (r.summary.avg_risk === null ? 'n/a' : r.summary.avg_risk.toFixed(2)) },
]

/**
 * Every route as a lane of straightened road on one shared mile scale, with the ranking figures
 * beside it, so the reason for the verdict can be read at a glance. A lane selects its route.
 */
export function RouteLanes({ data }: { data: AnalyzeResponse }) {
  const selected = useUi((s) => s.selectedRouteId)
  const select = useUi((s) => s.selectRoute)
  const rec = data.recommendation
  const longest = Math.max(...data.routes.map((r) => r.summary.distance_mi))
  const ranked = rec.ranking.map((id) => data.routes.find((r) => r.id === id)!).filter(Boolean)

  return (
    <div className="lanes" role="group" aria-label="Routes compared on one mile scale">
      <div className="lanes-head" aria-hidden>
        <span />
        <span />
        {COLUMNS.map((c) => (
          <span key={c.key} data-decides={rec.decided_by === c.key}>
            {c.caption}
          </span>
        ))}
      </div>
      {ranked.map((route) => (
        <button
          key={route.id}
          type="button"
          className="lane"
          aria-pressed={route.id === selected}
          data-recommended={route.id === rec.route_id && !doNotDepart(rec)}
          aria-label={`${route.label}: ${COLUMNS.map((c) => `${c.caption} ${c.value(route)}`).join(', ')}`}
          onClick={() => select(route.id)}
        >
          <span className="lane-plate">{plate(route.label)}</span>
          <LineDiagram route={route} scaleMi={longest} />
          {COLUMNS.map((c) => (
            <span key={c.key} className="lane-figure" data-decides={rec.decided_by === c.key}>
              {c.value(route)}
            </span>
          ))}
        </button>
      ))}
      <p className="lanes-key">Severe+ counts Severe and No Travel miles; High+ counts High and no-forecast miles.</p>
    </div>
  )
}

/** "Route A" → "A": the letter is the plate. */
function plate(label: string): string {
  return label.replace(/^Route\s+/i, '')
}

function miles(value: number): string {
  return `${(Math.round(value * 10) / 10).toLocaleString('en-US')}`
}
