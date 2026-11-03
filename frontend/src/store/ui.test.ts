import { beforeEach, describe, expect, it } from 'vitest'
import { useUi } from './ui'

describe('ui store', () => {
  beforeEach(() => useUi.getState().reset('r2'))

  it('starts a new analysis on the recommended route at departure hour', () => {
    useUi.getState().setHour(12)
    useUi.getState().reset('r1')

    expect(useUi.getState()).toMatchObject({ selectedRouteId: 'r1', hour: 0, openCheckpoint: null })
  })

  it('opening a checkpoint also selects its route', () => {
    useUi.getState().openCheckpointAt({ routeId: 'r3', idx: 4 })

    expect(useUi.getState()).toMatchObject({ selectedRouteId: 'r3', openCheckpoint: { routeId: 'r3', idx: 4 } })
  })

  it('switching route closes a popup that belonged to the previous route', () => {
    useUi.getState().openCheckpointAt({ routeId: 'r2', idx: 1 })
    useUi.getState().selectRoute('r1')

    expect(useUi.getState()).toMatchObject({ selectedRouteId: 'r1', openCheckpoint: null })
  })

  it('ignores repeated hover on the same checkpoint so the table and map do not re-render', () => {
    useUi.getState().hoverCheckpoint({ routeId: 'r1', idx: 2 })
    const before = useUi.getState().hoveredCheckpoint

    useUi.getState().hoverCheckpoint({ routeId: 'r1', idx: 2 })

    expect(useUi.getState().hoveredCheckpoint).toBe(before)
  })
})
