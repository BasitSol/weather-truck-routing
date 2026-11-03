import type { Route } from '../../api/types'
import { LevelTag } from '../../components/LevelIcon'
import { dayChanges, formatLocal } from '../../lib/time'
import { useUi } from '../../store/ui'

/** Every checkpoint of the selected route; rows link to the map marker and its popup. */
export function CheckpointTable({ route, intervalMi }: { route: Route; intervalMi: number }) {
  const hovered = useUi((s) => s.hoveredCheckpoint)
  const open = useUi((s) => s.openCheckpoint)
  const hover = useUi((s) => s.hoverCheckpoint)
  const openAt = useUi((s) => s.openCheckpointAt)
  const newDay = dayChanges(route.checkpoints)

  return (
    <section className="checkpoints" aria-labelledby="checkpoints-title">
      <h2 id="checkpoints-title" className="section-title">
        {route.label} checkpoints, every {intervalMi} mi
      </h2>
      <div className="cp-scroll">
      <table className="cp-table">
        <thead>
          <tr>
            <th scope="col">Mile</th>
            <th scope="col">Arrival</th>
            <th scope="col" className="num">
              Wind <span className="unit">mph</span>
            </th>
            <th scope="col" className="num">
              Rain <span className="unit">in/h</span>
            </th>
            <th scope="col" className="num">
              Snow <span className="unit">in/h</span>
            </th>
            <th scope="col">Risk</th>
          </tr>
        </thead>
        <tbody>
          {route.checkpoints.flatMap((cp, i) => {
            const ref = { routeId: route.id, idx: cp.idx }
            const isHot = hovered?.routeId === route.id && hovered.idx === cp.idx
            const isOpen = open?.routeId === route.id && open.idx === cp.idx
            const explain = cp.risk !== 0
            const w = cp.weather
            const rowProps = {
              'data-hot': isHot || isOpen,
              // Row groups alternate tone instead of rules between rows.
              'data-stripe': i % 2 === 1,
              onMouseEnter: () => hover(ref),
              onMouseLeave: () => hover(null),
              onClick: () => openAt(ref),
            }
            const rows = [
              <tr
                key={cp.idx}
                className="cp-row"
                tabIndex={0}
                aria-label={`Mile ${Math.round(cp.mile)}, ${cp.driver}. Show on map.`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    openAt(ref)
                  }
                }}
                onFocus={() => hover(ref)}
                onBlur={() => hover(null)}
                {...rowProps}
              >
                <td className="figure">{Math.round(cp.mile)}</td>
                <td className="figure">
                  <ArrivalTime iso={cp.eta_utc} tz={cp.tz} newDay={newDay[i]} />
                </td>
                <td className="figure num">{w ? w.wind_mph.toFixed(1) : 'n/a'}</td>
                <td className="figure num">{w ? w.rain_in_hr.toFixed(2) : 'n/a'}</td>
                <td className="figure num">{w ? w.snow_in_hr.toFixed(2) : 'n/a'}</td>
                <td>
                  <LevelTag level={cp.risk} />
                </td>
              </tr>,
            ]
            if (explain) {
              rows.push(
                <tr key={`${cp.idx}-why`} className="cp-why" aria-hidden {...rowProps}>
                  <td />
                  <td colSpan={5}>{cp.driver}</td>
                </tr>,
              )
            }
            return rows
          })}
        </tbody>
      </table>
      </div>
    </section>
  )
}

/**
 * "Mon 13:00 MST". At phone width the weekday shows only where the local date changes, so an
 * overnight trip still says which day each time belongs to; the zone always shows.
 */
function ArrivalTime({ iso, tz, newDay }: { iso: string; tz: string; newDay: boolean }) {
  const [day, ...rest] = formatLocal(iso, tz).split(' ')
  return (
    <>
      <span className="cp-day" data-new-day={newDay}>
        {day}{' '}
      </span>
      {rest.join(' ')}
    </>
  )
}
