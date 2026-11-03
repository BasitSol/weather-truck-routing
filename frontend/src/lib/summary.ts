import type { Recommendation, Route } from '../api/types'
import { levelInfo } from './risk'

/** One plain sentence on what a route's weather looks like, for its ticket. */
export function routeSummaryLine(route: Route): string {
  const worst = route.summary.worst
  if (worst <= 0) return worst === 0 ? 'Low risk the whole way.' : 'No forecast for this route.'
  const first = route.segments.find((s) => s.risk === worst)
  const miles = route.summary.miles[levelInfo(worst).key]
  return `${levelInfo(worst).label} for ${Math.round(miles)} mi, first around mile ${Math.round(first?.from_mi ?? 0)}.`
}

/** Miles at the precision the ranking compares (0.1 mi), as the API's own sentences write them: "25.2 mi", "90 mi". */
export function formatMi(miles: number): string {
  return `${(Math.round(miles * 10) / 10).toLocaleString('en-US', { maximumFractionDigits: 1 })} mi`
}

/** The API leads its warnings with "Do not depart" when even the recommended route crosses No Travel. */
export function doNotDepart(rec: Recommendation): boolean {
  return rec.warnings[0]?.startsWith('Do not depart') ?? false
}

/**
 * Whether a warning adds something the route rows don't already say. "Route B crosses 90 mi of
 * No-Travel conditions." repeats that row's own No Travel figure, so it is left out.
 */
export function routeNoticeOnly(warning: string): boolean {
  return !/^Route \S+ crosses .* of No-Travel conditions\.$/.test(warning)
}
