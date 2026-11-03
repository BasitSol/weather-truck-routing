import { useId } from 'react'
import type { Level } from '../api/types'
import { levelInfo } from '../lib/risk'

const MARK = 'var(--asphalt-0)' // the dark legend printed on a sign
const PAINT = 'var(--paint)'

/**
 * Risk drawn as road signs, so no level is colour alone (docs/DESIGN.md): a round go-dot for Low,
 * the yellow warning diamond for Moderate, a warning diamond with "!" for High, an octagon with a
 * bar for Severe, a striped barricade for No Travel and a dashed ring for no forecast.
 */
export function LevelIcon({ level, size = 16 }: { level: Level; size?: number }) {
  const ink = levelInfo(level).ink
  const clip = useId()
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden className="level-icon">
      {level === 0 && (
        <>
          <circle cx="8" cy="8" r="6.5" fill={ink} />
          <path d="M5 8.2l2 2 4-4.2" fill="none" stroke={MARK} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </>
      )}
      {(level === 1 || level === 2) && (
        <>
          <path d="M8 .8 15.2 8 8 15.2.8 8z" fill={ink} />
          <path d="M8 2.9 13.1 8 8 13.1 2.9 8z" fill="none" stroke={MARK} strokeWidth="0.9" />
          {level === 2 && (
            <>
              <rect x="7.15" y="4.6" width="1.7" height="4.4" rx="0.5" fill={MARK} />
              <circle cx="8" cy="10.7" r="1" fill={MARK} />
            </>
          )}
        </>
      )}
      {level === 3 && (
        <>
          <path d="M5.3 1h5.4L15 5.3v5.4L10.7 15H5.3L1 10.7V5.3z" fill={ink} />
          <rect x="3.8" y="7" width="8.4" height="2" rx="0.4" fill={PAINT} />
        </>
      )}
      {level === 4 && (
        <>
          <clipPath id={clip}>
            <rect x="0.8" y="4" width="14.4" height="8" rx="1" />
          </clipPath>
          <g clipPath={`url(#${clip})`}>
            <rect x="0" y="0" width="16" height="16" fill={ink} />
            {[-6, -0.5, 5, 10.5].map((x) => (
              <path key={x} d={`M${x} 13 L${x + 4} 3 L${x + 6.6} 3 L${x + 2.6} 13z`} fill={PAINT} />
            ))}
          </g>
        </>
      )}
      {level === -1 && (
        <>
          <circle cx="8" cy="8" r="6" fill="none" stroke={ink} strokeWidth="1.8" strokeDasharray="2.6 1.9" />
          <circle cx="8" cy="8" r="1.5" fill={ink} />
        </>
      )}
    </svg>
  )
}

/** Icon + label, the way every level is written in the app. */
export function LevelTag({ level, className = '' }: { level: Level; className?: string }) {
  return (
    <span className={`level-tag ${className}`} data-level={level}>
      <LevelIcon level={level} size={15} />
      {levelInfo(level).label}
    </span>
  )
}
