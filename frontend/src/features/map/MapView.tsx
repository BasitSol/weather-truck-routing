import {
  type GeoJSONSource,
  Map as MapLibre,
  type MapLayerMouseEvent,
  Marker,
  NavigationControl,
  Popup,
  setWorkerUrl,
} from 'maplibre-gl'
// MapLibre finds its worker relative to its own module URL, which a bundler moves. Let Vite
// bundle the worker (with its shared chunk) and tell MapLibre where it ended up.
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { AnalyzeResponse } from '../../api/types'
import { boundsOf, checkpointCollection, checkpointFeatureId, heatCollection, routeCollection } from '../../lib/geojson'
import { type CheckpointRef, useUi } from '../../store/ui'
import { sampleCollection } from '../trip/samples'
import { CheckpointCard } from './CheckpointCard'
import { pinPlacement } from './pinPlacement'
import { SOURCES, addLayers, addReflectorImages, applySelection, heatColor, heatOpacity } from './layers'

setWorkerUrl(workerUrl)

const STYLE_URL = import.meta.env.VITE_MAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/dark'
const ASPHALT_GROUND = '#171614' // the basemap's land, matched to the panel's asphalt
const US_CENTER: [number, number] = [-98.5, 39.4]
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** The MapLibre canvas. The map instance lives in a ref; React never re-creates it. */
export default function MapView({
  data,
  onSample,
}: {
  data: AnalyzeResponse | null
  /** First run: a sample trip line was clicked. */
  onSample?: (name: string) => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const onSampleRef = useRef(onSample)
  const mapRef = useRef<MapLibre | null>(null)
  const dataRef = useRef(data)
  const [ready, setReady] = useState(false)
  const [popupNode] = useState(() => document.createElement('div'))
  const popupRef = useRef<Popup | null>(null)
  const samplePins = useRef<Marker[]>([])

  const selected = useUi((s) => s.selectedRouteId)
  const hoveredSegment = useUi((s) => s.hoveredSegment)
  const hoveredCheckpoint = useUi((s) => s.hoveredCheckpoint)
  const openCheckpoint = useUi((s) => s.openCheckpoint)

  useEffect(() => {
    dataRef.current = data
    onSampleRef.current = onSample
  }, [data, onSample])

  // 1. Create the map once.
  useEffect(() => {
    const map = new MapLibre({
      container: container.current!,
      style: STYLE_URL,
      center: US_CENTER,
      zoom: 3.4,
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
    })
    map.touchZoomRotate.disableRotation()
    // The dark basemap style names a few icons its sprite doesn't ship; draw them as nothing.
    map.setMissingStyleImageResolver((id) => {
      if (!map.hasImage(id)) map.addImage(id, { width: 1, height: 1, data: new Uint8Array(4) })
    })
    map.addControl(new NavigationControl({ showCompass: false }), 'bottom-right')
    mapRef.current = map

    map.on('load', () => {
      for (const layer of map.getStyle().layers) {
        if (layer.type === 'background') map.setPaintProperty(layer.id, 'background-color', ASPHALT_GROUND)
      }
      addReflectorImages(map)
      addLayers(map)
      setReady(true)
    })

    const ui = useUi.getState
    const routeLayers = ['route-line', 'route-unknown', 'route-no-travel']
    map.on('click', routeLayers, (e: MapLayerMouseEvent) => {
      const id = e.features?.[0]?.properties?.route_id
      if (id) ui().selectRoute(String(id))
    })
    map.on('click', 'checkpoints', (e: MapLayerMouseEvent) => {
      const p = e.features?.[0]?.properties
      if (p) ui().openCheckpointAt({ routeId: String(p.route_id), idx: Number(p.idx) })
    })
    map.on('mousemove', 'checkpoints', (e: MapLayerMouseEvent) => {
      const p = e.features?.[0]?.properties
      if (p) ui().hoverCheckpoint({ routeId: String(p.route_id), idx: Number(p.idx) })
    })
    map.on('mouseleave', 'checkpoints', () => ui().hoverCheckpoint(null))
    const sampleLayers = ['sample-line']
    map.on('click', sampleLayers, (e: MapLayerMouseEvent) => {
      const name = e.features?.[0]?.properties?.name
      if (name) onSampleRef.current?.(String(name))
    })
    for (const layer of [...routeLayers, 'checkpoints', ...sampleLayers]) {
      map.on('mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'))
      map.on('mouseleave', layer, () => (map.getCanvas().style.cursor = ''))
    }

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // 2. New analysis: push data into the existing sources and frame the routes.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const routes = data?.routes ?? []
    ;(map.getSource(SOURCES.routes) as GeoJSONSource).setData(routeCollection(routes))
    ;(map.getSource(SOURCES.checkpoints) as GeoJSONSource).setData(checkpointCollection(routes))
    ;(map.getSource(SOURCES.heat) as GeoJSONSource).setData(heatCollection(data?.heatmap.points ?? []))
    // First run shows the sample trips; any analysis replaces them with its own start and end.
    const samples = routes.length ? [] : sampleCollection().features
    ;(map.getSource(SOURCES.samples) as GeoJSONSource).setData({ type: 'FeatureCollection', features: samples })
    // Sample-trip names as HTML buttons in the app's own type, set off to one side of each line's
    // midpoint so they never cover the trip's end markers.
    for (const pin of samplePins.current) pin.remove()
    samplePins.current = samples.map((f) => {
      const [start, end] = f.geometry.coordinates as [[number, number], [number, number]]
      const button = document.createElement('button')
      button.type = 'button'
      button.className = 'sample-pin'
      button.setAttribute('aria-label', f.properties.label)
      // Name and load as two spans, so a phone can stack them into a narrower label.
      for (const [cls, text] of [['sample-pin-name', f.properties.name], ['sample-pin-sep', ', '], ['sample-pin-load', f.properties.load]]) {
        const span = document.createElement('span')
        span.className = cls
        span.textContent = text
        button.append(span)
      }
      button.addEventListener('click', () => onSampleRef.current?.(f.properties.name))
      return new Marker({ element: button, ...pinPlacement(map.project(start), map.project(end)) })
        .setLngLat([(start[0] + end[0]) / 2, (start[1] + end[1]) / 2])
        .addTo(map)
    })
    const endpoints: [number, number][][] = routes.length
      ? [[routes[0].segments[0].coordinates[0], routes[0].segments.at(-1)!.coordinates.at(-1)!]]
      : samples.map((f) => f.geometry.coordinates as [number, number][])
    ;(map.getSource(SOURCES.ends) as GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: endpoints.flatMap(([start, end]) => [
        { type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: end }, properties: { kind: 'destination' } },
        { type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: start }, properties: { kind: 'origin' } },
      ]),
    })
    const hour = useUi.getState().hour
    map.setPaintProperty('heat', 'circle-color', heatColor(hour))
    map.setPaintProperty('heat', 'circle-opacity', heatOpacity(hour))
    const bounds = routes.length ? boundsOf(routes) : lineBounds(samples.map((f) => f.geometry.coordinates))
    const narrow = map.getContainer().clientWidth < 640 // the legend takes the top of a phone map
    // On a phone the sample trips sit left, leaving room on the right for their labels.
    const padding = !narrow
      ? { top: 72, bottom: 150, left: 72, right: 72 }
      : routes.length
        ? { top: 120, bottom: 40, left: 100, right: 100 }
        : { top: 120, bottom: 40, left: 64, right: 150 }
    map.fitBounds(bounds, {
      padding,
      duration: reducedMotion() || !routes.length ? 0 : 900,
    })
  }, [data, ready])

  // 3. Route selection: restyle via paint properties.
  useEffect(() => {
    const map = mapRef.current
    if (map && ready) applySelection(map, selected)
  }, [selected, ready])

  // 4. Line-diagram hover outlines one stretch.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    map.setFilter(
      'route-focus',
      hoveredSegment
        ? ['all', ['==', ['get', 'route_id'], hoveredSegment.routeId], ['==', ['get', 'from_mi'], hoveredSegment.fromMi]]
        : ['==', ['get', 'route_id'], ''],
    )
  }, [hoveredSegment, ready])

  // 5. Table/map hover share one highlighted checkpoint through feature-state.
  useEffect(() => {
    const map = mapRef.current
    const id = featureId(dataRef.current, hoveredCheckpoint)
    if (!map || !ready || id === null) return
    map.setFeatureState({ source: SOURCES.checkpoints, id }, { hover: true })
    return () => {
      if (map.getSource(SOURCES.checkpoints)) map.setFeatureState({ source: SOURCES.checkpoints, id }, { hover: false })
    }
  }, [hoveredCheckpoint, ready])

  // 6. Popup for the open checkpoint; React renders its content into the popup's node.
  const openRoute = data?.routes.find((r) => r.id === openCheckpoint?.routeId)
  const openCp = openRoute?.checkpoints.find((c) => c.idx === openCheckpoint?.idx)
  useEffect(() => {
    const map = mapRef.current
    // Clear the ref before removing: remove() fires 'close' synchronously, and the close handler
    // must not mistake this replacement for the user dismissing the popup.
    const previous = popupRef.current
    popupRef.current = null
    previous?.remove()
    if (!map || !ready || !openCp) return
    // closeOnClick is off so a click on another checkpoint switches the popup instead of closing it.
    const popup = new Popup({ closeButton: true, closeOnClick: false, maxWidth: '300px', offset: 12, focusAfterOpen: false })
      .setLngLat([openCp.lon, openCp.lat])
      .setDOMContent(popupNode)
      .addTo(map)
    popup.on('close', () => {
      if (popupRef.current === popup) useUi.getState().openCheckpointAt(null)
    })
    popupRef.current = popup
    if (!map.getBounds().contains([openCp.lon, openCp.lat])) {
      map.easeTo({ center: [openCp.lon, openCp.lat], duration: reducedMotion() ? 0 : 600 })
    }
  }, [openCp, ready, popupNode])

  // 7. Forecast hour: subscribe outside React and repaint at most once per frame.
  useEffect(() => {
    if (!ready) return
    let frame = 0
    const unsubscribe = useUi.subscribe((state, prev) => {
      if (state.hour === prev.hour) return
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const map = mapRef.current
        if (!map) return
        map.setPaintProperty('heat', 'circle-color', heatColor(state.hour))
        map.setPaintProperty('heat', 'circle-opacity', heatOpacity(state.hour))
      })
    })
    return () => {
      cancelAnimationFrame(frame)
      unsubscribe()
    }
  }, [ready])

  return (
    <>
      <div ref={container} className="map-canvas" role="region" aria-label="Route map" />
      {openRoute && openCp && createPortal(<CheckpointCard route={openRoute} cp={openCp} />, popupNode)}
    </>
  )
}

function featureId(data: AnalyzeResponse | null, ref: CheckpointRef | null): number | null {
  if (!data || !ref) return null
  const index = data.routes.findIndex((r) => r.id === ref.routeId)
  return index < 0 ? null : checkpointFeatureId(index, ref)
}

function lineBounds(lines: GeoJSON.Position[][]): [[number, number], [number, number]] {
  const pts = lines.flat()
  const lons = pts.map((p) => p[0])
  const lats = pts.map((p) => p[1])
  return [
    [Math.min(...lons), Math.min(...lats)],
    [Math.max(...lons), Math.max(...lats)],
  ]
}
