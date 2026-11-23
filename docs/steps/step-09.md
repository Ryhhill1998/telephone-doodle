> Suggested reading (in docs/plan/): 04-ui-design-brief.md

### Step 9. Drawing canvas component

Branch `feat/canvas`. Requires Step 7 approved.

A standalone, well-tested component, not yet wired into the game.

- **Stroke format** (shared with the backend as an opaque JSON blob):
  ```json
  { "v": 1, "w": 800, "h": 600,
    "ops": [
      { "t": "s", "color": "#222222", "size": 4, "pts": [[0.127, 0.147], [0.131, 0.150]] },
      { "t": "f", "color": "#F08A24", "x": 0.40, "y": 0.55 } ] }
  ```
  Logical canvas is fixed 4:3 (800×600). Points are stored as 0..1 fractions of width and height so drawings render correctly at any display size. A drawing is an ordered list of **operations**: `s` is a brush stroke (the eraser is a white stroke), `f` is a **flood fill** at a point. Rendering replays the operations in order; a fill is computed on an offscreen 800×600 canvas (scanline flood fill with a small colour tolerance so anti-aliased edges don't leak) and then scaled to the display size, so every device shows the same result. Cache the rendered bitmap so a `StrokeView` does not redo fills on every paint. Undo removes the last operation.
- `DrawingCanvas` (editable): Pointer Events (`pointerdown/move/up/cancel`), `touch-action: none`, correct handling of `devicePixelRatio` and CSS resizing, smoothing via quadratic curves between points, the 14-colour palette and eraser from section 4, a **custom colour picker** (the custom swatch opens a popover with a hue slider and a saturation/brightness square, or the browser's native colour input if that proves more reliable on iOS; tell me which you chose, and keep the last few custom colours as extra swatches), a **brush-size slider** (an `<input type="range">`, 2 to 40, with a live preview dot; stroke `size` is stored in logical canvas pixels), a **Fill tool** (tap inside a region to fill it with the selected colour; eraser colour makes it fill with white), icon-only **Undo** (removes the last operation) and **Clear**, all with accessible labels and 44px targets. Throttle or simplify points to keep payloads small.
- `StrokeView` (read-only renderer) reusing the same drawing function, used later in guessing and the reveal.
- Pure helper functions in `frontend/src/lib/strokes.ts` (normalise, simplify, serialise, size estimate) and a **pure flood-fill function over a pixel buffer** (`Uint8ClampedArray`, width, height, seed, colour, tolerance) in `frontend/src/lib/floodfill.ts`, with vitest unit tests (fill a closed shape, fill does not leak through a closed outline, tolerance handling, filling an already-filled area is a no-op, edge and corner seeds). jsdom has no real canvas, so canvas behaviour itself is covered by component tests with a mocked 2D context (the right operations are produced for pointer sequences; undo and clear) and by the Playwright suite in Step 12.
- A dev-only `/sandbox` route to try the canvas.

**Review checklist:** works with mouse, touch and stylus (test on a phone via the dev server on the LAN if possible); a typical drawing serialises to well under 50 KB; no scroll or zoom gestures hijack drawing on iOS.

---
