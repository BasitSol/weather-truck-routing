// Map sources and layers. Created once when the map loads; afterwards only data, paint and filters
// change (setData / setPaintProperty / setFilter), so nothing is rebuilt while the user interacts.

import type { ExpressionSpecification, LayerSpecification, Map as MapLibre } from 'maplibre-gl'
import { LEVELS, levelColorExpression, levelInfo } from '../../lib/risk'

export const SOURCES = { routes: 'routes', checkpoints: 'checkpoints', heat: 'heat', ends: 'ends', samples: 'samples' } as const
const EMPTY: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

const ROUTE_COLOR = levelColorExpression(['get', 'risk']) as ExpressionSpecification
const ASPHALT = '#12110f' // casing and marker cores: the road surface
const PAINT = '#eeece4' // lane paint: markers, sample trips, the selected route's centre line

/** Colour for the corridor heat at hour h: one property lookup, swapped in a single frame. */
export function heatColor(hour: number): ExpressionSpecification {
  return levelColorExpression(['get', `r${hour}`]) as ExpressionSpecification
}

/** Calm stretches are bare road; hazards edge the route without burying its lines. */
export function heatOpacity(hour: number): ExpressionSpecification {
  return ['match', ['get', `r${hour}`], 0, 0, 1, 0.24, 2, 0.34, 3, 0.42, 4, 0.55, 0.2]
}

const isSelected = (selected: string | null): ExpressionSpecification => ['==', ['get', 'route_id'], selected ?? '']

export function routeOpacity(selected: string | null): ExpressionSpecification {
  return ['case', isSelected(selected), 1, 0.38]
}

export function routeWidth(selected: string | null, scale = 1): ExpressionSpecification {
  return [
    'interpolate', ['linear'], ['zoom'],
    4, ['case', isSelected(selected), 5.5 * scale, 2.5 * scale],
    10, ['case', isSelected(selected), 9 * scale, 4 * scale],
  ]
}

export function routeSortKey(selected: string | null): ExpressionSpecification {
  return ['case', isSelected(selected), 1, 0]
}

export function addLayers(map: MapLibre): void {
  for (const id of Object.values(SOURCES)) map.addSource(id, { type: 'geojson', data: EMPTY })

  const layers: LayerSpecification[] = [
    {
      id: 'heat',
      type: 'circle',
      source: SOURCES.heat,
      paint: {
        'circle-color': heatColor(0),
        'circle-opacity': heatOpacity(0),
        'circle-blur': 0.45,
        'circle-radius': ['interpolate', ['exponential', 1.6], ['zoom'], 3, 5, 5, 9, 7, 18, 9, 44, 11, 100],
      },
    },
    {
      // Outline under the stretch hovered in a route's line diagram.
      id: 'route-focus',
      type: 'line',
      source: SOURCES.routes,
      filter: ['==', ['get', 'route_id'], ''],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': PAINT, 'line-width': ['interpolate', ['linear'], ['zoom'], 4, 11, 10, 16] },
    },
    {
      id: 'route-casing',
      type: 'line',
      source: SOURCES.routes,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ASPHALT, 'line-width': routeWidth(null, 1.9), 'line-opacity': routeOpacity(null) },
    },
    {
      id: 'route-line',
      type: 'line',
      source: SOURCES.routes,
      filter: ['!=', ['get', 'risk'], -1],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ROUTE_COLOR, 'line-width': routeWidth(null), 'line-opacity': routeOpacity(null) },
    },
    {
      // Unknown: no forecast, drawn dashed so missing data never looks like a calm road.
      id: 'route-unknown',
      type: 'line',
      source: SOURCES.routes,
      filter: ['==', ['get', 'risk'], -1],
      layout: { 'line-cap': 'butt', 'line-join': 'round' },
      paint: {
        'line-color': ROUTE_COLOR,
        'line-width': routeWidth(null),
        'line-opacity': routeOpacity(null),
        'line-dasharray': [1.2, 1.2],
      },
    },
    {
      // No Travel: a doubled line, readable without colour.
      id: 'route-no-travel',
      type: 'line',
      source: SOURCES.routes,
      filter: ['==', ['get', 'risk'], 4],
      layout: { 'line-cap': 'butt', 'line-join': 'round' },
      // Barricade: white stripes across the No-Travel red, so it reads without its colour.
      paint: {
        'line-color': PAINT,
        'line-width': routeWidth(null, 0.6),
        'line-dasharray': [0.9, 0.9],
        'line-opacity': routeOpacity(null),
      },
    },
    {
      // Signature: the selected route carries a dashed lane-paint centre line over its risk colour.
      id: 'route-paint',
      type: 'line',
      source: SOURCES.routes,
      filter: ['==', ['get', 'route_id'], ''],
      layout: { 'line-cap': 'butt', 'line-join': 'round' },
      paint: {
        'line-color': PAINT,
        'line-width': ['interpolate', ['linear'], ['zoom'], 4, 1.6, 10, 2.6],
        'line-dasharray': [3, 2.5],
        'line-opacity': 0.9,
      },
    },
    {
      // Checkpoints as cat's-eye road reflectors: an asphalt housing with a risk-coloured lens,
      // turned to lie along the road.
      id: 'checkpoint-reflectors',
      type: 'symbol',
      source: SOURCES.checkpoints,
      layout: {
        'icon-image': ['concat', 'reflector-', ['to-string', ['get', 'risk']]],
        'icon-rotate': ['-', ['get', 'bearing'], 90],
        'icon-rotation-alignment': 'map',
        'icon-allow-overlap': true,
        'icon-ignore-placement': true,
        'icon-size': ['interpolate', ['linear'], ['zoom'], 4, 0.5, 5, 0.55, 9, 1, 12, 1.25],
        'symbol-sort-key': routeSortKey(null),
      },
      paint: { 'icon-opacity': reflectorOpacity(null) },
    },
    {
      // Invisible hit target over each reflector; draws a paint ring only on hover.
      id: 'checkpoints',
      type: 'circle',
      source: SOURCES.checkpoints,
      paint: checkpointRing(null),
    },
    {
      // First run: the sample trips as dashed start-to-destination lines, clickable to run.
      id: 'sample-line',
      type: 'line',
      source: SOURCES.samples,
      filter: ['==', ['geometry-type'], 'LineString'],
      layout: { 'line-cap': 'round' },
      paint: { 'line-color': PAINT, 'line-width': 2.5, 'line-dasharray': [2, 2], 'line-opacity': 0.85 },
    },
    {
      id: 'ends',
      type: 'circle',
      source: SOURCES.ends,
      paint: {
        'circle-radius': 7,
        'circle-color': ['case', ['==', ['get', 'kind'], 'origin'], PAINT, ASPHALT],
        'circle-stroke-color': PAINT,
        'circle-stroke-width': 3,
      },
    },
  ]
  // Risk layers go under the basemap's place labels so city names stay readable; the clickable
  // markers stay on top.
  const firstLabel = map.getStyle().layers.find((l) => l.type === 'symbol')?.id
  for (const layer of layers) {
    const onTop = ['checkpoint-reflectors', 'checkpoints', 'ends'].includes(layer.id)
    map.addLayer(layer, onTop ? undefined : firstLabel)
  }
}

/** Restyle every route-bound layer for the selected route. Paint/layout only, no rebuild. */
export function applySelection(map: MapLibre, selected: string | null): void {
  for (const id of ['route-casing', 'route-line', 'route-unknown', 'route-no-travel']) {
    map.setPaintProperty(id, 'line-opacity', routeOpacity(selected))
    map.setLayoutProperty(id, 'line-sort-key', routeSortKey(selected))
  }
  map.setPaintProperty('route-casing', 'line-width', routeWidth(selected, 1.9))
  map.setPaintProperty('route-line', 'line-width', routeWidth(selected))
  map.setPaintProperty('route-unknown', 'line-width', routeWidth(selected))
  map.setPaintProperty('route-no-travel', 'line-width', routeWidth(selected, 0.6))
  // No centre line over missing data or a barricade, which already carries its own paint.
  map.setFilter('route-paint', ['all', isSelected(selected), ['!=', ['get', 'risk'], -1], ['!=', ['get', 'risk'], 4]])
  map.setPaintProperty('checkpoint-reflectors', 'icon-opacity', reflectorOpacity(selected))
  map.setLayoutProperty('checkpoint-reflectors', 'symbol-sort-key', routeSortKey(selected))
  const ring = checkpointRing(selected)
  map.setPaintProperty('checkpoints', 'circle-radius', ring['circle-radius'])
  map.setPaintProperty('checkpoints', 'circle-stroke-opacity', ring['circle-stroke-opacity'])
}

/**
 * Zoomed out, only reflectors about 20 miles apart show, so they read as studs with lane paint
 * between them rather than a chain; from zoom 8 every checkpoint shows.
 */
function reflectorOpacity(selected: string | null): ExpressionSpecification {
  const full: ExpressionSpecification = ['case', isSelected(selected), 1, 0.4]
  return ['interpolate', ['linear'], ['zoom'], 7, ['case', ['get', 'major'], full, 0], 8, full]
}

/** The checkpoint hit target: transparent, a little larger on the selected route, a ring on hover. */
function checkpointRing(selected: string | null) {
  const hover: ExpressionSpecification = ['boolean', ['feature-state', 'hover'], false]
  return {
    'circle-color': ASPHALT,
    'circle-opacity': 0,
    'circle-radius': [
      'interpolate', ['linear'], ['zoom'],
      4, ['case', isSelected(selected), 6, 3],
      10, ['case', isSelected(selected), 12, 6],
    ] as ExpressionSpecification,
    'circle-stroke-color': PAINT,
    'circle-stroke-width': 2.5,
    'circle-stroke-opacity': ['case', hover, 1, 0] as ExpressionSpecification,
  }
}

/** Cat's-eye reflector sprites, one per risk level, drawn once at 2x for crisp edges. */
export function addReflectorImages(map: MapLibre): void {
  const ratio = 2
  for (const level of LEVELS) {
    const id = `reflector-${level}`
    if (map.hasImage(id)) continue
    const canvas = document.createElement('canvas')
    canvas.width = 18 * ratio
    canvas.height = 12 * ratio
    const g = canvas.getContext('2d')
    if (!g) return
    g.scale(ratio, ratio)
    g.fillStyle = ASPHALT // housing
    g.beginPath()
    g.roundRect(0.5, 0.5, 17, 11, 3)
    g.fill()
    g.strokeStyle = 'rgba(238, 236, 228, 0.55)'
    g.lineWidth = 1
    g.stroke()
    g.fillStyle = levelInfo(level).color // lens
    g.beginPath()
    g.roundRect(3.5, 3, 11, 6, 2)
    g.fill()
    g.fillStyle = PAINT // glint
    g.fillRect(5, 4, 2.5, 1.5)
    map.addImage(id, g.getImageData(0, 0, canvas.width, canvas.height), { pixelRatio: ratio })
  }
}
