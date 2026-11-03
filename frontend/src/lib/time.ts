// Time zones matter here: a trip from Denver to Chicago crosses two of them, and a dispatcher may
// plan from a third. Departure is entered in the origin's wall clock; every ETA is shown in the
// local time of the place it describes.

const HOUR_MS = 3_600_000

function parts(date: Date, tz: string, extra: Intl.DateTimeFormatOptions = {}) {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
    ...extra,
  })
  const out: Record<string, string> = {}
  for (const p of fmt.formatToParts(date)) out[p.type] = p.value
  return out
}

/** Minutes the zone is ahead of UTC at that instant (Denver in winter: −420). */
function offsetMinutes(tz: string, date: Date): number {
  const p = parts(date, tz)
  const asUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second)
  return Math.round((asUtc - Math.floor(date.getTime() / 1000) * 1000) / 60_000)
}

function formatOffset(minutes: number): string {
  const sign = minutes < 0 ? '-' : '+'
  const abs = Math.abs(minutes)
  return `${sign}${String(Math.floor(abs / 60)).padStart(2, '0')}:${String(abs % 60).padStart(2, '0')}`
}

/** "2026-11-03T08:00" read in `tz` → "2026-11-03T08:00:00-07:00". */
export function wallTimeToISO(wall: string, tz: string): string {
  const [date, time] = wall.split('T')
  const [y, m, d] = date.split('-').map(Number)
  const [hh, mm] = time.split(':').map(Number)
  const guess = Date.UTC(y, m - 1, d, hh, mm)
  let offset = offsetMinutes(tz, new Date(guess))
  offset = offsetMinutes(tz, new Date(guess - offset * 60_000)) // settle across a DST edge
  return `${wall.slice(0, 16)}:00${formatOffset(offset)}`
}

export function tzAbbr(tz: string, at: Date = new Date()): string {
  return parts(at, tz, { timeZoneName: 'short' }).timeZoneName ?? tz
}

/** "Tue 08:31 MST" in the given zone. */
export function formatLocal(iso: string | Date, tz: string): string {
  const date = typeof iso === 'string' ? new Date(iso) : iso
  const p = parts(date, tz, { weekday: 'short', timeZoneName: 'short' })
  return `${p.weekday} ${p.hour}:${p.minute} ${p.timeZoneName}`
}

/** Slider label: local time at the origin for `hour` after departure. */
export function hourLabel(startIso: string, hour: number, tz: string): string {
  const at = new Date(new Date(startIso).getTime() + hour * HOUR_MS)
  return `${formatLocal(at, tz)}, ${hour === 0 ? 'departure' : `+${hour} h`}`
}

export function formatDuration(minutes: number): string {
  const total = Math.round(minutes)
  const h = Math.floor(total / 60)
  const m = total % 60
  return h ? `${h} h ${m} min` : `${m} min`
}

/** Next full hour plus one, as a wall time in `tz` for a datetime-local input. */
export function defaultDepartureWall(tz: string, now: Date = new Date()): string {
  const p = parts(now, tz)
  const t = new Date(Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour + 2))
  return t.toISOString().slice(0, 16)
}

/** The current wall time in `tz`, for the datetime input's min attribute. */
export function nowWall(tz: string, now: Date = new Date()): string {
  const p = parts(now, tz)
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`
}

export function browserTz(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
}

/** For each stop, whether its local calendar date differs from the stop before (the first always does). */
export function dayChanges(stops: { eta_utc: string; tz: string }[]): boolean[] {
  const dates = stops.map((s) => {
    const p = parts(new Date(s.eta_utc), s.tz)
    return `${p.year}-${p.month}-${p.day}`
  })
  return dates.map((d, i) => i === 0 || d !== dates[i - 1])
}
