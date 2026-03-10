# Rendering Package

Visual output generation for piano falling notes visualization.

## Purpose

The rendering package handles all image generation, color management, and visual effects. It transforms MIDI data and timing information into pixel arrays for video output.

## Architecture

**Core Components:**
- `colors.py` — ColorScheme class with 6 color modes and velocity-based brightness
- `keyboard.py` — KeyboardRenderer, renders 88-key piano keyboard with key depression
- `layout.py` — Layout dataclass, maps time/MIDI to pixel coordinates
- `notes.py` — FallingNotesRenderer, draws falling note bars with per-note color cache
- `themes.py` — Theme presets (6 built-in) and auto-selection based on metadata

**Effects Subdirectory:** `effects/` (see effects/AGENTS.md)

## Key Design Patterns

**Coordinate System**
- y=0 is top of screen
- y=keyboard_top is boundary between note area and keyboard
- Keyboard occupies bottom keyboard_height pixels
- Notes render above keyboard_top only

**Color Caching**
- FallingNotesRenderer caches note colors on first render: `{(midi, start_seconds): rgb}`
- Each note gets fixed color across all frames (no flickering)
- Color transitions ripple in as new notes appear

**PIL Image Rendering**
- Core: PIL Image/ImageDraw for static elements
- Numpy arrays for pixel-level effects and gradients
- Additive blending for effects overlays

## Module Reference

### colors.py

**ColorScheme class**

Mutable attributes:
- `single_color` — base color for single mode (default cyan)
- `white_key_note_color` — key_type mode: white keys (default green)
- `black_key_note_color` — key_type mode: black keys (default blue)
- `palette` — custom 12-color chromatic palette (overrides CHROMATIC_COLORS)

Methods:
- `note_color(midi_number, velocity=1.0, part_index=0)` → RGBA tuple
- `note_color_rgb(midi_number, velocity=1.0)` → RGB tuple

**Modes:**
- `single` — uniform color, velocity modulates brightness (0.7–1.0x)
- `rainbow` — 12 chromatic colors from CHROMATIC_COLORS, octave brightening
- `neon` — 12 neon colors from NEON_PALETTE, octave brightening
- `part` — distinct color per part index, 4 colors in _PART_COLORS
- `pitch_range` — HSV gradient low-to-high notes (warm to cool)
- `key_type` — white/black key distinction, velocity brightness

### keyboard.py

**KeyboardRenderer class**

Constructor:
- `layout` — Layout instance for dimensions
- `color_scheme` — ColorScheme instance
- `key_depression` — bool, enable key press shadow effect

Methods:
- `render(active_notes: {midi: velocity})` → PIL RGB Image

Behavior:
- Draws all 88 keys (white first, black on top)
- Highlights active keys with note color
- Key depression effect: 3px shadow at top of white keys, 2px for black
- Returns keyboard_height-tall image

### layout.py

**Layout dataclass**

Attributes:
- `width`, `height` — output video dimensions
- `fps` — frames per second
- `keyboard_height_ratio` — fraction of screen (default 0.15)
- `lookahead_seconds` — duration of note fall animation (default 3.0)
- `piano_min_midi`, `piano_max_midi` — A0 (21) to C8 (108)

Properties:
- `keyboard_top` — y pixel where keyboard begins
- `keyboard_height` — pixels tall for keyboard
- `note_area_height` — keyboard_top (area above keyboard)

Methods:
- `time_to_y(note_time, current_time)` → float y pixel
  - Maps current_time to keyboard_top
  - Maps current_time + lookahead_seconds to y=0

### notes.py

**FallingNotesRenderer class**

Constructor:
- `layout` — Layout instance
- `color_scheme` — ColorScheme instance
- `key_map` — {midi: KeyInfo} from build_key_map()
- `note_duration_ratio` — visual length vs actual duration (default 0.95)
- `guide_lines` — draw vertical C/F guidelines (default True)
- `glitter` — enable sparkle on note bars (default False)
- `velocity_effect` — scale brightness by velocity (default False)

Methods:
- `render_guide_lines(img)` — draw C/F note boundaries
- `render(img, visible_notes, current_time)` → PIL RGB Image

Rendering Details:
- Per-note color cached on first render
- Rounded rectangles with corner radius 4
- Vertical white-to-color gradient (base_intensity 0.7)
- Velocity effect scales gradient intensity (0.3–1.0x)
- Glitter adds procedural sparkling (hash-based seed per note)
- Guide lines render last to stay on top

### themes.py

**Theme dataclass**

Frozen structure:
- `name`, `label` — identifier and display name
- `background_color` — RGB tuple
- `palette` — tuple of 12 chromatic colors

**THEMES dict**
- `classic` — vibrant PianiCast-style colors
- `midnight` — cool blue tones
- `sunset` — warm orange/red tones
- `ocean` — teal/cyan tones
- `neon` — bright saturated colors
- `pastel` — muted soft colors

**auto_select_theme(metadata: dict) → Theme**
- Fast tempo (>140 bpm) → neon
- Slow tempo (<72 bpm) → ocean
- Minor key → midnight
- Major key → sunset
- Default → classic

## Dependencies

- PIL (Pillow) — image creation/manipulation
- numpy — pixel array operations, broadcasting

## Common Patterns

**Rendering Pipeline**
```python
# In generator.py (main loop):
layout = Layout(width=1280, height=720)
colors = ColorScheme(mode="key_type")
notes_renderer = FallingNotesRenderer(layout, colors, key_map)
keyboard_renderer = KeyboardRenderer(layout, colors)
effects = VisualEffects()

for frame, (visible_notes, active_keys) in enumerate(timeline):
    img = Image.new("RGB", (layout.width, layout.height), bg_color)
    img = notes_renderer.render(img, visible_notes, current_time)
    keyboard_img = keyboard_renderer.render(active_keys)
    img.paste(keyboard_img, (0, layout.keyboard_top))
    img = effects.apply_*(img, ...)
    video.write_frame(img)
```

**Adding a New Color Mode**
1. Add method `_mode_color()` to ColorScheme
2. Add branch in `note_color()` dispatch
3. Update docstring with mode description

**Adding a New Effect**
- Create mixin in `effects/`
- Implement effect method with signature matching existing effects
- Inherit in VisualEffects
- Initialize state in VisualEffects.__init__
- Call from renderer loop with gating flag
