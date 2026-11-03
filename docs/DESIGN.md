---
name: Weather-Aware Truck Routing
description: The interstate at night, read by headlight. Warm asphalt ground, lane-paint ink, and a risk palette that is the only colour.
colors:
  asphalt-0: "#12110f"
  asphalt-1: "#191816"
  asphalt-2: "#211f1c"
  asphalt-3: "#2b2825"
  asphalt-4: "#38342f"
  map-ground: "#171614"
  paint: "#eeece4"
  paint-hover: "#ffffff"
  paint-2: "#b9b5ad"
  paint-3: "#999389"
  sign-black: "#121416"
  risk-low: "#2FBF7A"
  risk-low-ink: "#4FD392"
  risk-moderate: "#F2C230"
  risk-moderate-ink: "#F5CD4E"
  risk-high: "#F7862D"
  risk-high-ink: "#FA9A4C"
  risk-severe: "#F0435A"
  risk-severe-ink: "#F4677A"
  risk-no-travel: "#D9233F"
  risk-no-travel-ink: "#F26E80"
  risk-unknown: "#7E868E"
  risk-unknown-ink: "#A3AAB1"
typography:
  display:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "52px"
    fontWeight: 800
    lineHeight: 1.05
    fontFeature: "tnum"
  headline:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1.05
  headline-panel:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.2
  sign-letter:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 800
    lineHeight: 1
  title:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.45
  figure:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    fontFeature: "tnum"
  body:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum"
  label:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 700
  caption:
    fontFamily: "'Atkinson Hyperlegible Next Variable', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
rounded:
  plate: "4px"
  track: "3px"
  strip: "2px"
spacing:
  space-1: "4px"
  space-2: "8px"
  space-3: "12px"
  space-4: "16px"
  space-5: "24px"
  space-6: "32px"
components:
  button-primary:
    backgroundColor: "{colors.paint}"
    textColor: "{colors.asphalt-0}"
    rounded: "{rounded.plate}"
    height: "50px"
  button-primary-hover:
    backgroundColor: "{colors.paint-hover}"
  button-recheck:
    backgroundColor: "{colors.paint}"
    textColor: "{colors.asphalt-0}"
    rounded: "{rounded.plate}"
    padding: "0 16px"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.asphalt-3}"
    textColor: "{colors.paint}"
    rounded: "{rounded.plate}"
    padding: "0 14px"
    height: "36px"
  button-secondary-hover:
    backgroundColor: "{colors.paint}"
    textColor: "{colors.asphalt-0}"
  text-input:
    backgroundColor: "{colors.asphalt-2}"
    textColor: "{colors.paint}"
    rounded: "{rounded.plate}"
    padding: "0 12px"
    height: "44px"
  text-input-hover:
    backgroundColor: "{colors.asphalt-3}"
  segment-selected:
    backgroundColor: "{colors.paint}"
    textColor: "{colors.asphalt-0}"
    rounded: "{rounded.plate}"
  load-sign-plate:
    backgroundColor: "{colors.paint}"
    textColor: "{colors.sign-black}"
    rounded: "{rounded.plate}"
    padding: "16px 20px 14px"
  verdict-board:
    backgroundColor: "{colors.asphalt-2}"
    textColor: "{colors.paint}"
    rounded: "{rounded.plate}"
    padding: "22px 18px 18px"
  verdict-plate:
    backgroundColor: "{colors.paint}"
    textColor: "{colors.sign-black}"
    rounded: "{rounded.plate}"
    size: "52px x 52px"
  route-ticket:
    backgroundColor: "transparent"
    textColor: "{colors.paint}"
    rounded: "{rounded.plate}"
    padding: "14px 12px"
  route-ticket-hover:
    backgroundColor: "{colors.asphalt-2}"
  route-ticket-selected:
    backgroundColor: "{colors.asphalt-2}"
  lane-plate:
    backgroundColor: "{colors.asphalt-4}"
    textColor: "{colors.paint}"
    rounded: "{rounded.plate}"
    size: "24px x 22px"
  lane-plate-recommended:
    backgroundColor: "{colors.paint}"
    textColor: "{colors.sign-black}"
  stamp:
    backgroundColor: "{colors.asphalt-3}"
    textColor: "{colors.paint}"
    rounded: "{rounded.plate}"
    padding: "4px 9px"
  map-status:
    backgroundColor: "{colors.asphalt-0}"
    textColor: "{colors.paint}"
    rounded: "{rounded.plate}"
    padding: "12px 14px"
  sample-pin:
    backgroundColor: "{colors.asphalt-0}"
    textColor: "{colors.paint}"
    rounded: "{rounded.plate}"
    padding: "4px 9px"
  sample-pin-hover:
    backgroundColor: "{colors.paint}"
    textColor: "{colors.sign-black}"
---

# Design System: Weather-Aware Truck Routing

## Overview

**Creative North Star: "Asphalt at Night"**

The interstate after dark, read by headlight. Warm asphalt in tonal steps (bitumen and aggregate, not dashboard graphite) is the ground, lane-paint white is the ink and the one action colour, and the retroreflective risk palette is the only hue, so every colour on screen means danger or safety. The world rejects the light-grey panel with one blue accent and the broadsheet hairline look; the previous "Scale House" light world is retired.

Density is that of a working instrument: a fixed left panel of trip form and results beside a full-bleed dark map. Areas separate by tone; where parts of a result need a divider, it is dashed lane paint. Road furniture supplies the signature devices: the load weight on a white weight-limit sign plate, route letters on small sign plates, the verdict's lit letter plate, risk levels as road signs, a red-and-white barricade wherever travel is closed, a dashed lane-paint centre line on the selected route, cat's-eye reflectors for checkpoints, and every route laid on one shared mile scale.

**Key Characteristics:**
- Five warm asphalt tones carry all structure; the only dividers are dashed lane paint.
- Lane-paint white marks text and anything pressable; selected states invert to paint.
- Risk colours are the only hues, each with a lighter ink variant for text and icons; No Travel is always a striped barricade.
- One typeface, Atkinson Hyperlegible Next, set at 700, with 800 kept for sign lettering; tabular figures everywhere.
- 4px stamped-plate corners on every sign, field, control and panel.

## Colors

A warm near-black asphalt ramp with one warm off-white, plus six risk colours tuned to read like retroreflective sheeting on dark tarmac.

### Primary
- **Lane Paint** (paint): body text, the Analyze and "Check leaving at" buttons, selected segments, selected rows and lane rings, the sign-plate face, the verdict plate, barricade stripes, map markers, sample-trip lines, lane-dash dividers and the selected route's centre line. It is the one action colour; hover lifts it to Pure White (paint-hover).

### Neutral
- **Shoulder Black** (asphalt-0): the shell bar, route casing on the map, reflector housings, the map status chip, the mobile forecast band, text and sign marks on paint or risk fills.
- **Night Asphalt** (asphalt-1): the panel and page ground, and the floating legend and forecast dock at 94–95%.
- **Worn Asphalt** (asphalt-2): fields, inputs, the trip facts strip, the verdict board, the error ticket, hovered and selected route rows, the checkpoint table, popups.
- **Patched Asphalt** (asphalt-3): hover state, raised strips inside a field (swap button, stamps, line-diagram track, progress track), selected lanes.
- **Seam Asphalt** (asphalt-4): idle letter plates, slider track, scrollbar thumb; the darkest tone that still reads as an edge.
- **Map Ground** (map-ground): the basemap land colour and the map's loading fill, repainted over OpenFreeMap's dark style so the map sits on the panel's asphalt.
- **Faded Paint** (paint-2) and **Ghost Paint** (paint-3): secondary and tertiary text, captions, idle tick labels. Ghost Paint holds 4.5:1 on every asphalt tone up to asphalt-3.
- **Sign Black** (sign-black): the legend, inner border and printed rule on the white sign plate, the verdict plate's border, and text on lit plates. The plate carries its own greys for idle marks, track and lamp sockets; they never leave the plate.

### Risk palette (the only hues)
- **Low / Moderate / High / Severe / No Travel / Unknown** (risk-low through risk-unknown): fills on the map, line diagrams, the forecast hour strip, legend swatches and heat circles. No Travel is Barricade Red, deeper than Severe.
- **Ink variants** (risk-*-ink): the same hues lifted for text and icons on asphalt, at 4.5:1 or better. Field errors use Severe ink; invalid outlines use Severe. Warning notices are Moderate at 12% over asphalt.
- **Barricade** (`--barricade`: `repeating-linear-gradient(-45deg, #d9233f 0 4px, paint 4px 8px)`): No Travel wherever it is drawn as a line or band. The halt band draws it full size (12px stripes); the sign-plate lamp draws it deepened (#c41e36) with a sign-black rim.

### Named Rules
**The Tone Not Line Rule.** Areas and fields are separated by a step in asphalt tone, never by a grey hairline. The one divider is dashed lane paint (`--lane-dash`, paint at 30%, 14px dash, 12px gap, 2px tall) between route rows and between parts of a result; on the white sign plate, a 2px printed sign-black rule. Alternate checkpoint rows step up by a 2.5% white wash; a hot row steps to asphalt-3.

**The Only Hue Rule.** Every chromatic colour on screen is a risk level. Warnings, errors and lamps borrow the risk palette; there is no brand accent.

**The Pressable Paint Rule.** Lane paint fills only things you can press or things that are selected. Selected segments, pressed presets, highlighted suggestions and hovered secondary buttons all invert to paint on asphalt-0 text.

**The Readable Without Colour Rule.** Every level has its own road-sign icon shape. Unknown is always drawn dashed, and No Travel always carries white barricade stripes (map lines, lane strips, legend, hour strip, lamps, the halt band), so neither depends on hue.

## Typography

**Display Font:** Atkinson Hyperlegible Next Variable (with Atkinson Hyperlegible Next, system-ui)
**Body Font:** the same
**Label/Mono Font:** none; there is no monospace anywhere

**Character:** one face built for legibility at a glance, set bold (700) for anything that must be read from the cab and regular for explanation, with no negative tracking. Heavy (800) is sign lettering only. Tabular numerals are on at the root so every figure aligns.

### Hierarchy
- **Display** (800, 52px, 1.05): the load weight figure on the sign plate only; its unit is 20px/800.
- **Headline** (700, 34px, 1.05; 32px under 640px): the verdict title, "Take Route C" or "Do not depart".
- **Headline Panel** (700, 24px, 1.2; 22px under 640px, max 22ch, balanced): the first-screen title, "Three truck routes, scored by the weather where the truck will be".
- **Sign Letter** (800): the verdict plate letter at 30px and the lane plates at 13px.
- **Title** (700, 17px): section titles, route-row labels, route stops, forecast time.
- **Figure** (700, 14px): route-row, lane and trip-fact figures; the deciding lane figure goes to 800.
- **Body** (400, 15px, 1.45): running text; the first verdict reason and the halt line are 16px, later reasons 14px in paint-2, capped near 54ch.
- **Label** (700, 13px): field labels, place labels, samples title, the map status chip.
- **Caption** (400, 12px): help text, figure captions, column heads, tick labels in paint-3.

### Named Rules
**The One Face Rule.** Every role uses Atkinson Hyperlegible Next, including map attribution and popups. Hierarchy comes from weight (400 / 700 / 800) and size, not from a second family.

**The Sign Weight Rule.** 800 is reserved for lettering on a sign: the load numerals and unit, lane plates, the verdict plate and the deciding lane figure. Headings, labels and buttons are 700. No negative letter-spacing anywhere.

**The Aligned Figures Rule.** Numerals are tabular everywhere (`font-variant-numeric: tabular-nums` at the root), so miles, times and weights align in columns.

## Layout

Desktop is a two-column grid: a 464px panel on the left and the map filling the rest, under a 52px shell bar spanning both. The app is exactly the viewport height; the panel scrolls, the map does not. The legend floats top-right on the map and the forecast dock floats bottom-left, up to 640px wide.

Spacing runs on a 4px base (4, 8, 12, 16, 24, 32). Panel sections pad 24px; fields stack 18px apart; route rows sit edge to edge with a lane-dash between them. Departure and interval share one row so the Analyze button reaches the first viewport.

Status and failure come first in the panel. While a trip runs, a pending section at the top shows its From/To stops and a rolling lane-paint progress bar, and a status chip sits top-left on the map. An error ticket renders at the top of the panel; both scroll themselves into view.

Under 1024px the grid stacks shell, map (52vh), then panel; the forecast dock leaves the map and becomes a flat asphalt-0 band directly under it. Under 760px the idle dock is hidden and sample pins stack name over load. Under 640px side padding drops to 16px, the departure row stacks, the sign-plate caption hides, the legend tightens to the six levels in three columns without swatches, the map status chip moves to the bottom edge, and the forecast ticks keep only every 12 hours.

## Elevation & Depth

Flat by default. Depth inside the panel is tonal: each nested field is one asphalt step lighter than its ground (panel asphalt-1, board asphalt-2, selected lane asphalt-3). Only things floating over the map, or over the panel, take a shadow.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 10px 30px rgb(0 0 0 / 0.45), 0 2px 6px rgb(0 0 0 / 0.35)`): the legend, forecast dock, map status chip, place suggestions, map popups, map controls and sample pins. Never on in-panel fields.
- **Paint ring** (`box-shadow: inset 0 0 0 2px #eeece4`, 1.5px on lanes, stamps and pins): marks a selected route row, selected lane, the solid "Recommended" stamp and sample pins. It is a state marker, not a divider.
- **Sign border** (`box-shadow: inset 0 0 0 5px paint, inset 0 0 0 7px sign-black`): the black inner border of the white sign plate; the verdict plate uses the same at 3px and 5px.

### Named Rules
**The Float Only Over Map Rule.** A shadow means the element sits above the map or overlays content. Panel structure never casts one.

## Shapes

Stamped-plate geometry: 4px corners (`--radius`) on every sign, field, input, button, board, row, stamp, pin, legend and dock. Tracks step down to 3px (line diagrams, slider, legend swatches, lamps) and thin strips to 2px (hour strip, progress bar). Circles appear only as map start/destination markers (paint, or hollow with a paint ring), mirrored by the route block's form markers. Dashed paint lines are a native device of the world: the route-block spine, the trip-summary spine, sample trips on the map, the selected route's centre line, the lane-dash divider and the rolling progress bar. Diagonal red-and-white stripes belong to No Travel alone.

## Components

### Buttons
- **Shape:** stamped-plate corners (4px).
- **Primary:** the Analyze button, lane paint with asphalt-0 text, 50px tall, 16px at 700. Hover lifts to pure white; press nudges down 1px; disabled at 60% opacity. "Check leaving at …" is the same paint button at 40px and 14px.
- **Secondary:** Edit trip, Try again and similar, asphalt-3 with paint text, 36px tall, 13px at 700. Hover inverts to paint.
- **Presets and swap:** asphalt-2 or asphalt-3 chips that go asphalt-3 on hover and invert to paint when pressed.
- **Focus:** a 2px paint outline at 2px offset everywhere; on the sign plate the outline is sign-black.

### Inputs / Fields
- **Style:** borderless asphalt-2 fields, 44px tall, 4px corners; hover steps to asphalt-3.
- **Route block:** From and To as two 64px rows with paint markers (filled for start, hollow for destination) joined by a dashed paint-3 spine; the whole row carries the focus ring.
- **Segmented interval:** a 3px-padded asphalt-2 tray; the checked segment is lane paint.
- **Error:** 2px Severe outline inset, message in Severe ink at 13px/700.

### Risk Icons
Authored SVG road signs, one shape per level, in risk ink with asphalt-0 or paint marks: Low a round go-dot with a check; Moderate the warning diamond; High the diamond with "!"; Severe an octagon with a paint bar; No Travel a striped barricade board; Unknown a dashed ring with a centre dot. Phosphor icons remain only for actions and notices (edit, retry, warning), never for risk.

### Load Sign Plate (signature)
The load weight on a white weight-limit sign: paint face, sign-black legend and inner border, the weight at 52px/800. Beneath it a scale track with hatched zones past 30,000 and 40,000 lb and threshold ticks that light in paint, then the rule list under a 2px printed sign-black rule, with no box behind it. Lamps glow when a rule applies: the No Travel lamp as a deepened barricade with a sign-black rim, the Severe lamp in deepened Severe. Unlit lamps are dim filled squares, never hollow.

### Verdict Board and Route Lanes (signature)
An asphalt-2 board. Normally the headline is a lit letter plate (52px paint square with the sign border, the route letter at 30px/800) beside "Take Route X" at 34px/700, then a stamp naming the deciding criterion. When the API warns "Do not depart", a 14px barricade band runs edge to edge across the top of the board, the headline becomes "Do not depart", a 16px line names the least exposed route and its No-Travel miles, and under a lane-dash the corridor forecast gives the earliest clear departure with a "Check leaving at …" button that re-runs the analysis (or says none is clear within 48 h).

Then the route lanes. Each lane is a pressable row: an A/B/C letter plate (asphalt-4, or lit in paint with sign-black text for the recommended route), the route's line diagram scaled to the longest route so all share one mile scale, then Severe+, High+ and Avg figures. The deciding column's head goes to paint at 700 and its figures to paint at 800; the others sit in paint-2. A selected lane takes asphalt-3 and a 1.5px paint ring. The lane tracks draw on once from the origin (0.6s, staggered 60ms), only under `prefers-reduced-motion: no-preference`. Reasons and the driving assumption follow; other warnings sit below the board as Moderate notices.

### Line Diagram
A 14px asphalt-3 track filled with risk-coloured stretches; Unknown stretches are dashed, No Travel is the barricade. A dashed dark centre line runs the full strip and checkpoints sit on it as small paint reflectors. Hovering a stretch brightens it and outlines that stretch on the map in paint.

### Route Rows
Route rows (tickets) in rank order, transparent on the panel with a lane-dash between them; the dashes stop beside a lit row. Each has a 17px/700 label, a solid paint-ringed "Recommended" stamp or a quiet "Rank n", the worst level as an icon tag in risk ink, one line of figures (distance, drive time with the extra over the fastest, arrival), a one-line summary and the miles at each level with their sign icons. Hover takes asphalt-2; the selected row is asphalt-2 with a 2px paint ring; the deciding figure is underlined in paint.

### Checkpoint Table
On an asphalt-2 field with a sticky header; rows alternate by tone in groups (row plus its reason line), the hovered or open checkpoint steps to asphalt-3. Figures right-aligned and tabular.

### Pending and Error
The pending section repeats the trip's From/To markers and spine above a 4px lane-progress bar: an asphalt-3 track with paint dashes (18px dash, 12px gap) rolling toward the destination, static under reduced motion. The map status chip (asphalt-0, float shadow, 13px/700) carries the same bar and a one-line status. The error ticket is an asphalt-2 field with a title, the message in paint-2 and a Try again button. No skeleton placeholders.

### Map
OpenFreeMap dark with its background repainted to map-ground; risk layers sit under the basemap's place labels so city names stay readable. Routes draw as asphalt-0 casing (1.9x width) under a risk-coloured line; unselected routes drop to 38% opacity and thinner. No Travel stretches add a paint overlay at 0.6x width dashed [0.9, 0.9], striping the red like a barricade. The selected route adds a dashed lane-paint centre line (dash 3, gap 2.5, 90% opacity), omitted on Unknown and No Travel stretches.

Checkpoints are cat's-eye reflectors: canvas-drawn sprites (asphalt housing with a faint paint edge, risk-coloured lens, paint glint) rotated to the road bearing. Below zoom 7 only checkpoints about 20 miles apart show, fading in to every checkpoint by zoom 8; off the selected route they sit at 40%. A transparent hit target draws a paint ring on hover. The checkpoint popup is an asphalt-2 card; its driver line sits under a lane-dash, with no inner box.

Corridor heat is soft-edged circles (blur 0.45) coloured by level at the chosen hour. Calm is bare road (Low at opacity 0); hazards edge the route at 0.24 (Moderate), 0.34 (High), 0.42 (Severe), 0.55 (No Travel), 0.2 (Unknown). The 0 to 48 h slider repaints the heat layer outside React, at most once per animation frame.

Before the first run, sample trips draw as dashed paint lines with HTML pins (asphalt-0, 1.5px paint ring, float shadow) placed on the line's normal, pushed 14px out from its midpoint, upward or rightward, so a pin never covers either end marker. Hover or focus inverts a pin to paint.

### Legend and Forecast Dock
Floating asphalt-1 plates at 94–95% opacity with the float shadow. The legend pairs each level's swatch (dashed for Unknown, barricade for No Travel) with its sign icon and label, then the start/destination markers; on a phone it keeps only the six levels. The dock holds a paint-thumbed slider whose track is a 49-cell hour strip: each cell is the worst corridor level that hour (Low as a 32% green wash, Unknown dashed, No Travel barricade). Under it, the departure tick lit in paint and a 14px/700 readout line with the level's icon, naming the share of the corridor at that level and the mile where it starts on the selected route.

## Do's and Don'ts

### Do:
- **Do** separate every area by an asphalt tone step (asphalt-0 to asphalt-4), and divide parts of a result only with dashed lane paint.
- **Do** reserve lane paint for text, pressable controls and selected states.
- **Do** draw Unknown dashed and No Travel as the striped barricade wherever risk is drawn.
- **Do** draw risk levels with their road-sign icons, never as colour alone.
- **Do** put every route on one shared mile scale when routes are compared.
- **Do** keep shadows to elements floating over the map or overlaying content.
- **Do** use risk ink, not the fill colour, for risk text and icons on asphalt.
- **Do** put status and errors at the top of the panel, where the result will appear.
- **Do** respect reduced motion; the lane draw-on is the only entrance animation and the lane-progress roll stops.

### Don't:
- **Don't** draw grey hairline borders or boxes between fields, rows or sections.
- **Don't** introduce any hue that is not a risk level, including a brand or link accent.
- **Don't** use red-and-white stripes for anything but No Travel.
- **Don't** set headings or labels at 800 or with negative tracking; 800 is sign lettering.
- **Don't** use a second typeface or monospace for figures; use tabular numerals.
- **Don't** let the white sign plate's greys leave the plate.
- **Don't** let route or heat layers cover the basemap's place labels.
