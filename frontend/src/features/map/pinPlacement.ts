import type { PositionAnchor } from 'maplibre-gl'

interface Point {
  x: number
  y: number
}

const GAP_PX = 14
const SLANT = 0.1 // about 6 degrees off level (or upright) counts as slanted

/**
 * Where a sample trip's label sits relative to its line's midpoint: pushed out perpendicular to
 * the line, upward (or rightward for an upright line), so it never covers either end marker.
 * The direction depends only on the line's screen angle, which zooming and panning keep.
 */
export function pinPlacement(a: Point, b: Point): { anchor: PositionAnchor; offset: [number, number] } {
  const len = Math.hypot(b.x - a.x, b.y - a.y) || 1
  // One of the two normals; flip it to point up, or right when the line is upright.
  let nx = -(b.y - a.y) / len
  let ny = (b.x - a.x) / len
  if (ny > 0.01 || (Math.abs(ny) <= 0.01 && nx < 0)) {
    nx = -nx
    ny = -ny
  }
  // A centred label can be wider than a short trip, so any slant takes a corner anchor: the label
  // then grows away from the line on the side where the line falls away, never over an end.
  const vertical = ny < -SLANT ? 'bottom' : ''
  const horizontal = nx > SLANT ? 'left' : nx < -SLANT ? 'right' : ''
  const anchor = ([vertical, horizontal].filter(Boolean).join('-') || 'bottom') as PositionAnchor
  return { anchor, offset: [nx * GAP_PX, ny * GAP_PX] }
}
