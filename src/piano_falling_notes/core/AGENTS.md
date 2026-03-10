# AGENTS.md - piano_falling_notes.core (Core Rendering Pipeline)

Central coordination layer for video generation: configuration, main orchestrator, and shared rendering functions.

## Files

### Config (`config.py`)
**Dataclass holding all user-facing settings**

- **I/O**: `input_path`, `output_path`
- **Video**: `width`, `height`, `fps`, `crf` (quality)
- **Layout**: `keyboard_height_ratio`, `lookahead_seconds`
- **Colors**: `background_color`, `color_mode`, `single_note_color`, `white_key_note_color`, `black_key_note_color`, `note_opacity`, `theme`, `custom_background`
- **Keyboard**: `white_key_color`, `black_key_color`, `active_key_glow`
- **Effects**: `glow_enabled`, `glow_intensity`, `particles_enabled`, `note_border_radius`, `neon_burst`, `guide_lines`, `note_duration_ratio`, `glitter`, `comet_effect`, `comet_trail_glow`, `energy_color`, `starflow`
- **Audio**: `no_audio`, `audio_file`, `soundfont`, `reverb`
- **Layout modes**: `vertical` (portrait), `background_image`, `velocity_effect`, `pedal`, `key_depression`, `lead_in_seconds`, `tail_seconds`

Methods:
- `from_cli_and_yaml(args, config_file)` — Factory method merging CLI args and YAML config file

### Generator (`generator.py`)
**Main orchestrator: parses score, builds timeline, pre-computes energy, runs render loop, writes video**

Class: `VideoGenerator`

Method: `generate(config: Config) -> str`

12-step pipeline:
1. Parse MusicXML/MIDI via `parse_musicxml()` → notes list + metadata (tempo_bpm, key_signature, etc.)
2. Build timeline via `build_timeline()` → TimeIndex-indexed renderer-ready notes
3. Apply theme: auto-select or user-pick from THEMES dict; set background color
4. Load background image if specified
5. Setup rendering: Layout, ColorScheme, KeyboardRenderer, FallingNotesRenderer, VisualEffects
6. Calculate total frames from duration + lead_in + tail_seconds
7. Generate audio via `generate_audio()` (fluidsynth synthesis) or use external audio file
8. Initialize VideoWriter with output MP4 path
9. Pre-compute energy profile via `compute_energy_profile()` for energy-color mode
10. Run per-frame render loop:
    - For each frame 0..total_frames-1:
      - Get current_time = frame / fps
      - Render frame via `render_frame()` (see renderer.py)
      - Write frame to VideoWriter
      - Update progress bar
11. Finalize VideoWriter
12. Mux audio into video via `mux_video_audio()`; return output path

Key state:
- `timeline.notes` — All notes to render, indexed by TimeIndex
- `energy_map` — Pre-computed energy profile (int(seconds) → float(0-1))
- `_note_color_cache` — Per-note color assignments (persists across frames for stability)

### Renderer (`renderer.py`)
**Shared render pipeline used by CLI, web conversion, and web preview**

Functions:

#### `compute_energy_profile(timeline_notes, total_duration) -> dict`
Pre-compute 4s sliding window energy (note density + avg velocity) normalized to song's own range.

Returns: `{int(seconds) → float(0-1)}`

Steps:
1. For each second in total_duration, count notes in [t, t+4s) window
2. Compute density = count/4.0 and avg_velocity = sum(velocities)/count
3. Combine: raw_energy = density * 0.5 + avg_velocity * 0.5
4. 5-point moving average smoothing
5. Normalize relative to min/max of smoothed values (ensures full palette is always used)

#### `apply_energy_color(color_scheme, energy_map, current_time) -> None`
Apply energy-based color to color_scheme for current_time.

Palette mapping (energy 0-1 → color):
- 0-0.60 (60%): blue → green (PAL_LOW → PAL_MID)
- 0.60-0.90 (30%): green → orange/red (PAL_MID → PAL_HIGH)
- 0.90-1.0 (10%): orange/red (PAL_HIGH)

Mutates `color_scheme.single_color` and key colors for key_type mode.

#### `make_background_frame(config, background_img) -> Image`
Generate solid or image-based background frame.

Returns: PIL Image sized (config.width, config.height)

#### `render_frame(layout, color_scheme, keyboard, falling, effects, timeline_notes, time_index, config, current_time, background_img) -> Image`
Core 12-step per-frame rendering pipeline.

Steps:
1. Make background frame (solid or image)
2. Get active notes at current_time via time_index query
3. Apply energy color if enabled (mutates color_scheme)
4. Render falling notes via falling.render() — draws note bars + glow + glitter + guide lines
5. Render keyboard via keyboard.render() — draws keys + active key glow
6. Render starflow effect via effects.apply_starflow()
7. Render ascending bubbles via effects.apply_ascending_bubbles()
8. Render neon burst via effects.apply_neon_burst()
9. Render note glow via effects.apply_note_glow()
10. Render comet effect via effects.apply_c_note_rise()
11. Composite all layers into final frame
12. Return PIL Image

Modifies state:
- `color_scheme` — updated by apply_energy_color()
- `keyboard` — updated by render() with current active keys
- `falling` — updated by render() with current note colors
- `effects` — internal effect state (particles, bursts, comets)

## Key Concepts

### Energy-Based Color System
- Pre-computed per-second energy in generator.py before render loop
- Energy = normalized(density * 0.5 + avg_velocity * 0.5) over 4s window
- Palette transitions: blue (calm) → green (neutral) → orange/red (energetic)
- Applied each frame to note colors if `config.energy_color = True`

### Per-Note Color Caching
- FallingNotesRenderer maintains `_note_color_cache = {(midi, start_seconds): rgb}`
- Color assigned ONCE on first render of each note
- Ensures color stability across frames; new notes ripple in with new colors

### Render Pipeline Invariants
1. Background is always rendered first
2. Falling notes layer on top of background
3. Keyboard layer on top of falling notes
4. Effects particles layer on top of all
5. All compositing is done in-memory before writing to VideoWriter

## AI Agent Instructions

### When modifying rendering:

1. **Test energy color computation** before releasing:
   ```bash
   .venv/bin/python -m piano_falling_notes test-scores/Golden.mxl -o result/energy_test.mp4 \
     --width 1280 --height 720 --fps 30 --no-audio --color-mode single
   ```

2. **Per-note color cache must be respected** — do not reset colors mid-video or colors will flicker

3. **render_frame() must be stateless except for effect particle state** — no hidden dependencies on previous frames besides FallingNotesRenderer's cache

4. **Energy profile is immutable after compute** — do not modify energy_map in render loop

5. **Config.custom_background takes precedence over theme.background_color** — check this order in generator.py

6. **Lead-in and tail-out seconds** are added to total duration before frame calculation; ensure render loop respects this

## Typical Modification Patterns

### Adding a new global color property:
1. Add to Config (config.py)
2. Update ColorScheme (rendering/colors.py) if it needs to be applied per-frame
3. Update renderer.py if it needs to be part of apply_energy_color() or render_frame()
4. Test with standard test command

### Adjusting energy profile behavior:
1. Modify compute_energy_profile() window size or smoothing in renderer.py
2. Adjust palette thresholds in apply_energy_color() (currently 60%/30%/10%)
3. Test with `--color-mode single` or `key_type` to see energy color clearly

### Changing frame composition order:
1. Modify render_frame() step order
2. Be aware of z-order (layering depth) — keyboard should stay above falling notes, effects on top
3. Test with multiple notes and effects enabled

## Parent Modules

See `/Users/lee/projects/piano-falling-notes/src/piano_falling_notes/AGENTS.md` for package structure.
See `/Users/lee/projects/piano-falling-notes/AGENTS.md` for root project structure.
