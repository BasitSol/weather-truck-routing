import type { Route } from '../../api/types'
import { levelInfo } from '../../lib/risk'
import { useUi } from '../../store/ui'

/**
 * The route straightened into one strip of road, start to destination: risk stretches in mile
 * order under a dashed lane-paint centre line, a cat's-eye reflector at every checkpoint. Every
 * route is drawn on the same mile scale (`scaleMi`), so a longer route is a longer strip.
 */
export function LineDiagram({ route, scaleMi }: { route: Route; scaleMi: number }) {
  const hoverSegment = useUi((s) => s.hoverSegment)
  const length = route.summary.distance_mi || 1

  return (
    <div className="line-diagram" aria-hidden>
      <div className="line-road" style={{ width: `${(length / Math.max(scaleMi, length)) * 100}%` }}>
        <div className="line-track">
          {route.segments.map((s) => (
            <span
              key={s.from_mi}
              className="line-stretch"
              data-level={s.risk}
              style={{
                width: `${((s.to_mi - s.from_mi) / length) * 100}%`,
                // Unknown (dashed) and No Travel (doubled) take their line form from CSS.
                background: s.risk === -1 || s.risk === 4 ? undefined : levelInfo(s.risk).color,
              }}
              title={`${levelInfo(s.risk).label}, mile ${Math.round(s.from_mi)} to ${Math.round(s.to_mi)}`}
              onMouseEnter={() => hoverSegment({ routeId: route.id, fromMi: s.from_mi })}
              onMouseLeave={() => hoverSegment(null)}
            />
          ))}
          <span className="line-paint" />
          {route.checkpoints.map((cp) => (
            <span key={cp.idx} className="line-reflector" style={{ left: `${(cp.mile / length) * 100}%` }} />
          ))}
        </div>
        <span className="line-end tnum">{Math.round(length)} mi</span>
      </div>
    </div>
  )
}
