# M2 — Generative Visual Layers

## Purpose

M2 turns the video compositor into a mixed-media visual instrument. A generated visual is a first-class composition layer, not a temporary effect baked into the preview or a separate output-only widget.

Generator layers share the existing composition transform, opacity, blend, visibility, lock, z-order, project persistence and preview/projector pipeline.

## Available generator layers

### Geometry

Procedural transparent vector-style graphics rasterized on a 1600×900 canvas:

- Concentric rings
- Grids
- Radial constructions
- Crosshatch fields
- Nested regular polygons

Controls include pattern, density, primary/accent colour, line weight, layer transform and animation.

### Text Art

Editable multiline typographic compositions with:

- Typeface selection from installed system fonts
- Regular, medium, bold and black weights
- Font size and absolute letter tracking
- Line spacing and horizontal / vertical alignment
- Fill colour, outline colour and outline width
- Soft offset shadow

Text remains editable as layer data in the project. It is not permanently converted into a user-managed bitmap asset.

### Waveform

Procedural signal-like graphics that do not require an audio input:

- Parallel sine traces
- Lissajous curves
- Orbit patterns

Controls include density, amplitude, frequency, line weight and two-colour treatment. In M3, this generator can be connected to the audio analysis bus without making the drawing code depend on an audio device.

## Animation model

Static generator content is rasterized only when its visual settings change. Repeated frame animation is performed in the compositor shader:

| Animation | Behaviour |
|---|---|
| Pulse | Smooth scale modulation |
| Rotate | Oscillating rotation |
| Drift | Slow positional movement |
| Flicker | Controlled opacity modulation |
| None | Static layer |

Animation parameters are intentionally bounded and are applied independently of the cached content texture. This avoids re-rasterizing text and geometry every frame.

## Architecture

- core.composition.Layer stores generator_type and the serializable generator_settings dictionary.
- generators.catalog supplies defaults, type validation and parameter range normalization.
- generators.rasterizer.GeneratorRasterizer creates transparent RGBA images and caches them by a content fingerprint.
- core.render_engine.RenderEngine uploads each generator texture into its own ModernGL context.
- rendering.compositor.Compositor composites the generator through the same blend/opacity/transform path as video and applies GPU-side animation.
- Each output renderer owns its own GPU texture. Both consume the same saved layer settings and therefore show the same composition in preview and projector output.

Generator content is stored directly in .eliav projects through the existing composition serializer. Older projects remain compatible because generator fields are optional.

## Current boundaries

This first M2 increment does not yet include:

- GPU particle simulation and particle emitters
- Editable vector paths / bezier drawing
- Imported still-image and animated-media overlay layers
- Per-layer effect stacks
- Text motion presets such as crawl, type-on and glyph-by-glyph reveal
- User-defined generator presets and scene banks
- Audio-reactive controls (M3)

Those can be added without changing the generator-layer contract.
