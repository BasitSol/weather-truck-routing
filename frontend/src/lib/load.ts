// The brief's load rules compare weight with a strict ">" against these two thresholds.

export const MAX_LOAD_LB = 80_000 // US federal gross vehicle weight limit
export const NO_TRAVEL_RULE_LB = 30_000 // 45–54 mph + > 30,000 lb → No Travel
export const SEVERE_RULE_LB = 40_000 // 35–44 mph + > 40,000 lb → Severe

export interface LoadRules {
  noTravelAbove45: boolean
  severeAbove35: boolean
}

export function activeLoadRules(lb: number): LoadRules {
  return { noTravelAbove45: lb > NO_TRAVEL_RULE_LB, severeAbove35: lb > SEVERE_RULE_LB }
}

export function formatLb(lb: number): string {
  return Math.round(lb).toLocaleString('en-US')
}

export function parseLb(text: string): number | null {
  const digits = text.replace(/[,\s]|lbs?$/gi, '')
  if (!/^\d+$/.test(digits)) return null
  return Number(digits)
}
