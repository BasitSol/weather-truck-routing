import type { Level, MilesByLevel } from '../api/types'

export interface LevelInfo {
  level: Level
  label: string
  color: string // fill on the map and in diagrams; the only hues in the app
  ink: string // icon and text colour, ≥ 4.5:1 on the asphalt panel
  key: keyof MilesByLevel
}

const INFO: Record<Level, LevelInfo> = {
  0: { level: 0, label: 'Low', color: '#2FBF7A', ink: '#4FD392', key: 'low' },
  1: { level: 1, label: 'Moderate', color: '#F2C230', ink: '#F5CD4E', key: 'moderate' },
  2: { level: 2, label: 'High', color: '#F7862D', ink: '#FA9A4C', key: 'high' },
  3: { level: 3, label: 'Severe', color: '#F0435A', ink: '#F4677A', key: 'severe' },
  // Barricade red, deeper than Severe; wherever it is drawn as a line it carries white barricade stripes.
  4: { level: 4, label: 'No Travel', color: '#D9233F', ink: '#F26E80', key: 'no_travel' },
  [-1]: { level: -1, label: 'Unknown', color: '#7E868E', ink: '#A3AAB1', key: 'unknown' },
}

/** Display order: known levels low → high, then Unknown. */
export const LEVELS: Level[] = [0, 1, 2, 3, 4, -1]

export function levelInfo(level: Level): LevelInfo {
  return INFO[level]
}

/** MapLibre `match` expression mapping a numeric level property to its colour. */
export function levelColorExpression(property: unknown[]): unknown[] {
  return ['match', property, 0, INFO[0].color, 1, INFO[1].color, 2, INFO[2].color, 3, INFO[3].color, 4, INFO[4].color, INFO[-1].color]
}

export interface MilesRow {
  level: Level
  miles: number
  share: number
}

/** Non-zero levels on a route, worst first (Unknown last), with their share of the distance. */
export function milesBreakdown(miles: MilesByLevel): MilesRow[] {
  const total = Object.values(miles).reduce((a, b) => a + b, 0) || 1
  const order: Level[] = [4, 3, 2, 1, 0, -1]
  return order
    .map((level) => ({ level, miles: miles[INFO[level].key], share: Math.round((miles[INFO[level].key] / total) * 100) / 100 }))
    .filter((row) => row.miles > 0)
}
