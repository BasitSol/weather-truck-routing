import { create } from 'zustand'

export interface CheckpointRef {
  routeId: string
  idx: number
}

export interface SegmentRef {
  routeId: string
  fromMi: number
}

/** UI-only state. Server data lives in TanStack Query; the map instance lives in a ref. */
interface UiState {
  selectedRouteId: string | null
  hoveredCheckpoint: CheckpointRef | null
  openCheckpoint: CheckpointRef | null
  hoveredSegment: SegmentRef | null
  /** Corridor heat hour, 0…48 after departure. The map reads it outside React render. */
  hour: number
  selectRoute: (id: string) => void
  hoverCheckpoint: (ref: CheckpointRef | null) => void
  openCheckpointAt: (ref: CheckpointRef | null) => void
  hoverSegment: (ref: SegmentRef | null) => void
  setHour: (hour: number) => void
  reset: (selectedRouteId: string | null) => void
}

export const useUi = create<UiState>((set) => ({
  selectedRouteId: null,
  hoveredCheckpoint: null,
  openCheckpoint: null,
  hoveredSegment: null,
  hour: 0,
  selectRoute: (id) => set((s) => (s.selectedRouteId === id ? s : { selectedRouteId: id, openCheckpoint: null })),
  hoverCheckpoint: (ref) =>
    set((s) => {
      const cur = s.hoveredCheckpoint
      const same = cur === ref || (cur && ref && cur.routeId === ref.routeId && cur.idx === ref.idx)
      return same ? s : { hoveredCheckpoint: ref }
    }),
  openCheckpointAt: (ref) => set(ref ? { openCheckpoint: ref, selectedRouteId: ref.routeId } : { openCheckpoint: null }),
  hoverSegment: (ref) => set({ hoveredSegment: ref }),
  setHour: (hour) => set({ hour }),
  reset: (selectedRouteId) =>
    set({ selectedRouteId, hoveredCheckpoint: null, openCheckpoint: null, hoveredSegment: null, hour: 0 }),
}))
