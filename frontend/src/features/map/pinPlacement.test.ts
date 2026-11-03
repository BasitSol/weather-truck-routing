import { describe, expect, it } from 'vitest'
import { pinPlacement } from './pinPlacement'

// Screen points: x grows right, y grows down.
describe('pinPlacement', () => {
  it('sets a label above a level line', () => {
    const { anchor, offset } = pinPlacement({ x: 0, y: 100 }, { x: 200, y: 100 })
    expect(anchor).toBe('bottom')
    expect(offset[0]).toBeCloseTo(0)
    expect(offset[1]).toBeLessThan(0)
  })

  it('sets a label to the right of an upright line, clear of both ends', () => {
    const { anchor, offset } = pinPlacement({ x: 100, y: 0 }, { x: 100, y: 200 })
    expect(anchor).toBe('left')
    expect(offset[0]).toBeGreaterThan(0)
  })

  it('pushes a label up and right off a line falling to the right, away from its upper-left end', () => {
    // Salt Lake City (upper left) to Denver (lower right).
    expect(pinPlacement({ x: 0, y: 0 }, { x: 200, y: 120 }).anchor).toBe('bottom-left')
  })

  it('corner-anchors a short, slightly slanted trip so a wide label clears its raised end', () => {
    // Salt Lake City to Denver on a zoomed-out map: 220 px long, 20 px drop.
    expect(pinPlacement({ x: 876, y: 431 }, { x: 1097, y: 474 }).anchor).toBe('bottom-left')
  })

  it('gives the same side whichever end the line is drawn from', () => {
    // Dallas (lower right) to Denver (upper left).
    expect(pinPlacement({ x: 200, y: 200 }, { x: 0, y: 0 }).anchor).toBe('bottom-left')
  })

  it('pushes a label up and left off a line rising to the right', () => {
    expect(pinPlacement({ x: 0, y: 200 }, { x: 200, y: 0 }).anchor).toBe('bottom-right')
  })
})
