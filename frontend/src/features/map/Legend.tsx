import { LevelIcon } from '../../components/LevelIcon'
import { LEVELS, levelInfo } from '../../lib/risk'

export function Legend() {
  return (
    <aside className="legend" aria-label="Map legend">
      <ul className="legend-levels">
        {LEVELS.map((level) => (
          <li key={level}>
            <span className="legend-swatch" style={{ background: levelInfo(level).color }} data-level={level} />
            <LevelIcon level={level} size={13} />
            {levelInfo(level).label}
          </li>
        ))}
      </ul>
      <ul className="legend-lines">
        <li>
          <span className="legend-dot legend-dot-origin" />
          Start
        </li>
        <li>
          <span className="legend-dot" />
          Destination
        </li>
      </ul>
    </aside>
  )
}
