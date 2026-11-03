import { describe, expect, it } from 'vitest'
import { activeLoadRules, formatLb, parseLb } from './load'

describe('activeLoadRules', () => {
  it('has no load rule at or below 30,000 lb (the brief compares with strict >)', () => {
    expect(activeLoadRules(30_000)).toEqual({ noTravelAbove45: false, severeAbove35: false })
  })

  it('turns on the 45–54 mph rule above 30,000 lb', () => {
    expect(activeLoadRules(30_001)).toEqual({ noTravelAbove45: true, severeAbove35: false })
    expect(activeLoadRules(40_000)).toEqual({ noTravelAbove45: true, severeAbove35: false })
  })

  it('turns on both rules above 40,000 lb', () => {
    expect(activeLoadRules(40_001)).toEqual({ noTravelAbove45: true, severeAbove35: true })
  })
})

describe('lb formatting', () => {
  it('formats with thousands separators', () => {
    expect(formatLb(44000)).toBe('44,000')
  })

  it('parses what a person types', () => {
    expect(parseLb('44,000')).toBe(44000)
    expect(parseLb(' 35000 lb')).toBe(35000)
    expect(parseLb('')).toBeNull()
    expect(parseLb('abc')).toBeNull()
  })
})
