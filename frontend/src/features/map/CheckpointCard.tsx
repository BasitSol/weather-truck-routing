import type { Checkpoint, Route } from '../../api/types'
import { LevelTag } from '../../components/LevelIcon'
import { levelInfo } from '../../lib/risk'
import { formatLocal } from '../../lib/time'

/** Popup content for one checkpoint: where, when, what the weather is, and why it scored. */
export function CheckpointCard({ route, cp }: { route: Route; cp: Checkpoint }) {
  const w = cp.weather
  return (
    <div className="cp-card">
      <p className="cp-card-head">
        <span>
          {route.label}, mile <span className="tnum">{Math.round(cp.mile)}</span>
        </span>
        <LevelTag level={cp.risk} />
      </p>
      <p className="cp-card-eta">
        Arrives <span className="figure">{formatLocal(cp.eta_utc, cp.tz)}</span>
      </p>
      {w ? (
        <dl className="cp-card-wx">
          <div>
            <dt>Wind</dt>
            <dd className="figure">{w.wind_mph.toFixed(1)} mph</dd>
            {cp.levels.wind !== undefined && <dd className="cp-card-band">{levelInfo(cp.levels.wind).label}</dd>}
          </div>
          <div>
            <dt>Rain</dt>
            <dd className="figure">{w.rain_in_hr.toFixed(2)} in/h</dd>
            {cp.levels.rain !== undefined && <dd className="cp-card-band">{levelInfo(cp.levels.rain).label}</dd>}
          </div>
          <div>
            <dt>Snow</dt>
            <dd className="figure">{w.snow_in_hr.toFixed(2)} in/h</dd>
            {cp.levels.snow !== undefined && <dd className="cp-card-band">{levelInfo(cp.levels.snow).label}</dd>}
          </div>
        </dl>
      ) : null}
      <p className="cp-card-driver">{cp.driver}</p>
    </div>
  )
}
