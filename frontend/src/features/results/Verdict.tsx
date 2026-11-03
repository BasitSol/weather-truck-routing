import { ArrowClockwise, WarningCircle } from '@phosphor-icons/react'
import { type CSSProperties, useEffect, useRef } from 'react'
import type { AnalyzeResponse, DecidedBy, Route } from '../../api/types'
import { earliestClearDeparture } from '../../lib/laterDeparture'
import { levelInfo } from '../../lib/risk'
import { doNotDepart, formatMi, routeNoticeOnly } from '../../lib/summary'
import { formatLocal } from '../../lib/time'
import { RouteLanes } from './RouteLanes'

// What the stamp says, by the ranking criterion that separated the winner from the runner-up.
// "duration" only ever breaks a tie on every risk criterion, so the stamp says exactly that.
const DECIDED_BY: Record<DecidedBy, string> = {
  severe_miles: 'Decided by fewest Severe-or-worse miles',
  high_miles: 'Decided by fewest High miles',
  avg_risk: 'Decided by lowest average risk',
  duration: 'Risk tie, broken by travel time',
  only_route: 'Only route found',
  tie: 'Full tie on every criterion',
}

const HOUR_MS = 3_600_000

interface VerdictProps {
  data: AnalyzeResponse
  /** Re-run the same trip leaving `delayH` hours later. */
  onRecheck?: (delayH: number) => void
}

/**
 * The recommendation and the reason for it. When even the best route crosses No-Travel
 * conditions, the answer is "do not depart": that becomes the headline, the route is demoted to
 * the least exposed option, and the corridor forecast suggests when to try again.
 */
export function Verdict({ data, onRecheck }: VerdictProps) {
  const rec = data.recommendation
  const route = data.routes.find((r) => r.id === rec.route_id)!
  const halt = doNotDepart(rec)
  // Per-route No-Travel warnings repeat each route row's own figure, so only the rest are listed.
  const otherWarnings = (halt ? rec.warnings.slice(1) : rec.warnings).filter(routeNoticeOnly)
  const s = route.summary
  // A new result takes focus at its headline, so keyboard and screen-reader users land on the answer.
  const titleRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    titleRef.current?.focus({ preventScroll: false })
  }, [data])

  return (
    <section className="verdict" aria-labelledby="verdict-title">
      <div className="verdict-board" data-halt={halt} style={{ '--halt': levelInfo(4).color } as CSSProperties}>
        {halt && <div className="halt-band" aria-hidden />}
        <div className="verdict-head" role={halt ? 'alert' : undefined}>
          <h2 id="verdict-title" className="verdict-title" tabIndex={-1} ref={titleRef}>
            {halt ? (
              'Do not depart'
            ) : (
              <>
                <span className="verdict-plate" aria-hidden>
                  {route.label.replace(/^Route\s+/i, '')}
                </span>
                <span>Take {route.label}</span>
              </>
            )}
          </h2>
          {halt && (
            <p className="verdict-halt-line">
              {route.label} is the least exposed route, and it still crosses {formatMi(s.miles.no_travel)} of
              No-Travel conditions when leaving at {formatLocal(data.meta.departure_utc, data.meta.origin_tz)}.
            </p>
          )}
          <span className="stamp">{DECIDED_BY[rec.decided_by]}</span>
        </div>
        {halt && <LaterDeparture data={data} route={route} onRecheck={onRecheck} />}
        <RouteLanes data={data} />
        <div className="verdict-reasons">
          {rec.reasons.map((reason) => (
            <p key={reason}>{reason}</p>
          ))}
        </div>
        <p className="verdict-assumption">
          Arrival times assume continuous driving at typical truck speeds, without traffic delays or rest
          stops. Weather is read at each arrival time.
        </p>
      </div>
      {otherWarnings.length > 0 && (
        <ul className="notices">
          {otherWarnings.map((w) => (
            <li key={w} className="notice">
              <WarningCircle size={18} weight="fill" aria-hidden />
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/** When the corridor forecast says the recommended route clears, and a button to check that departure. */
function LaterDeparture({ data, route, onRecheck }: { data: AnalyzeResponse; route: Route } & Pick<VerdictProps, 'onRecheck'>) {
  const delay = earliestClearDeparture(route, data.heatmap.points, data.meta.departure_utc)
  if (delay === null) {
    return (
      <p className="later-departure">
        The 48 h corridor forecast shows No-Travel conditions on {route.label} for every departure it covers.
      </p>
    )
  }
  const when = formatLocal(new Date(Date.parse(data.meta.departure_utc) + delay * HOUR_MS), data.meta.origin_tz)
  return (
    <div className="later-departure">
      <p>
        The corridor forecast shows {route.label} clear of No-Travel conditions for a departure around{' '}
        <strong>{when}</strong>, {delay} h later.
      </p>
      {onRecheck && (
        <button type="button" className="recheck" onClick={() => onRecheck(delay)}>
          <ArrowClockwise size={16} weight="bold" aria-hidden />
          Check leaving at {when}
        </button>
      )}
    </div>
  )
}
