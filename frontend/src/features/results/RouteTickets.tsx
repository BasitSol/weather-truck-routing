import { useId } from 'react'
import type { AnalyzeResponse, DecidedBy, Route } from '../../api/types'
import { LevelIcon, LevelTag } from '../../components/LevelIcon'
import { levelInfo, milesBreakdown } from '../../lib/risk'
import { doNotDepart, routeSummaryLine } from '../../lib/summary'
import { formatDuration, formatLocal } from '../../lib/time'
import { useUi } from '../../store/ui'

/**
 * One row per route, in rank order like the lanes above: what its weather looks like, how long it
 * takes and when it arrives. Rows sit on the panel like lanes, with lane paint between them.
 * Selecting a row selects the route on the map.
 */
export function RouteTickets({ data }: { data: AnalyzeResponse }) {
  const selected = useUi((s) => s.selectedRouteId)
  const select = useUi((s) => s.selectRoute)
  const rec = data.recommendation
  const fastest = Math.min(...data.routes.map((r) => r.summary.duration_min))
  const ranked = rec.ranking.map((id) => data.routes.find((r) => r.id === id)).filter((r): r is Route => !!r)
  const halt = doNotDepart(rec)

  return (
    <section className="tickets" aria-label="Routes in ranked order">
      {ranked.map((route, i) => (
        <RouteTicket
          key={route.id}
          route={route}
          rank={i + 1}
          recommended={route.id === rec.route_id}
          halt={halt}
          selected={route.id === selected}
          extraMin={Math.round(route.summary.duration_min - fastest)}
          decidedBy={rec.decided_by}
          onSelect={() => select(route.id)}
        />
      ))}
    </section>
  )
}

interface TicketProps {
  route: Route
  rank: number
  recommended: boolean
  /** "Do not depart": the top route is only the least exposed one. */
  halt: boolean
  selected: boolean
  extraMin: number
  decidedBy: DecidedBy
  onSelect: () => void
}

function RouteTicket({ route, rank, recommended, halt, selected, extraMin, decidedBy, onSelect }: TicketProps) {
  const s = route.summary
  const standing = recommended ? (halt ? 'Least exposed' : 'Recommended') : null
  const rows = milesBreakdown(s.miles)
  const detailsId = useId()

  return (
    <button
      type="button"
      className="ticket"
      aria-pressed={selected}
      data-recommended={recommended}
      aria-label={`${route.label}, ${standing ? standing.toLowerCase() : `rank ${rank}`}. Show on the map.`}
      aria-describedby={detailsId}
      onClick={onSelect}
    >
      <span className="ticket-head">
        <span className="ticket-label">{route.label}</span>
        {standing ? (
          <span className="stamp stamp-solid" data-halt={halt}>
            {standing}
          </span>
        ) : (
          <span className="ticket-rank">Rank {rank}</span>
        )}
        <span className="ticket-worst">
          <LevelTag level={s.worst} />
        </span>
      </span>
      <span id={detailsId} className="ticket-body">
        <span className="ticket-figures">
          <span className="figure">{Math.round(s.distance_mi).toLocaleString('en-US')} mi</span>
          <span>
            <span className="figure" data-decides={decidedBy === 'duration'}>
              {formatDuration(s.duration_min)}
            </span>
            {extraMin > 0 && <span className="figure-sub"> +{formatDuration(extraMin)}</span>}
          </span>
          <span>
            arrives <span className="figure">{formatLocal(s.arrive_utc, s.arrive_tz)}</span>
          </span>
        </span>
        <span className="ticket-line">{routeSummaryLine(route)}</span>
        {/* One level end to end is already said by the sentence above; a mix gets its breakdown. */}
        {rows.length > 1 && (
        <span className="ticket-miles">
          {rows.map((row) => (
            <span key={row.level} className="ticket-mile">
              <LevelIcon level={row.level} size={13} />
              <span>
                {levelInfo(row.level).label} <span className="tnum">{Math.round(row.miles)}</span> mi
              </span>
            </span>
          ))}
        </span>
        )}
        {route.notices.map((n) => (
          <span key={n} className="ticket-notice">
            {n}
          </span>
        ))}
      </span>
    </button>
  )
}
