# AGENTS.md - piano_falling_notes (Package)

Top-level package coordinating CLI, config, and core rendering.

## Files

### Entry Point
- **`__main__.py`** — Main entry point called by `python -m piano_falling_notes` and `piano-falling-notes` CLI command
  - Parses args via `parse_args()` from cli.py
  - Dispatches to web mode or CLI conversion mode
  - Builds Config from CLI args + optional YAML config file
  - Instantiates `VideoGenerator` and calls `generate(config)`

### CLI
- **`cli.py`** — argparse definitions (parse_args function)
  - Positional arg: input file (MusicXML/MIDI: .musicxml, .mxl, .xml, .mid, .midi)
  - Output: `-o/--output` (default: <input_name>.mp4)
  - Config: `--config` (YAML file path, optional)
  - Video: `--width`, `--height`, `--fps`, `--crf`
  - Layout: `--lookahead` (seconds, default 3.0)
  - Colors: `--color-mode` (single/rainbow/neon/part/key_type), `--note-color`, `--white-key-color`, `--black-key-color`
  - Effects: `--no-glow`, `--no-comet`, `--no-energy-color`, `--no-starflow`, `--no-neon-burst`, `--no-guide-lines`, `--glitter`, `--comet-trail-glow`
  - Theme: `--theme` (auto/classic/midnight/sunset/ocean/neon/pastel), `--background` (hex color)
  - Audio: `--no-audio`, `--audio-file`, `--soundfont`, `--reverb`
  - Layout: `--vertical` (portrait mode, swaps width/height to 1080x1920), `--background-image` (jpg/png/webp)
  - Effects: `--velocity-effect`, `--pedal`, `--key-depression`
  - Web: `--web`, `--port`, `--host`

### Package Init
- **`__init__.py`** — Empty; package marker

## Subdirectories

Each subdirectory has its own AGENTS.md child documentation:

### Core (`core/`)
**Central coordination layer: config, generator (orchestrator), and shared rendering**

Files:
- `config.py` — Config dataclass with all settings (video dimensions, fps, color mode, effect toggles, theme, etc.)
- `generator.py` — Main orchestrator: parses score, builds timeline, pre-computes energy profile, runs render loop, writes video
- `renderer.py` — Shared render functions: render_frame() (12-step pipeline), compute_energy_profile(), make_background_frame(), apply_energy_color()

See `/Users/lee/projects/piano-falling-notes/src/piano_falling_notes/core/AGENTS.md`

### Parser (`parser/`)
**MusicXML/MIDI parsing and note extraction**

Files:
- `musicxml_parser.py` — Entry point for parsing .mxl, .musicxml, .xml files; uses music21 to extract notes + metadata
- `models.py` — Data classes for parser output

### Timeline (`timeline/`)
**Note timeline building and indexing**

Files:
- `builder.py` — Converts parser notes into renderer-ready timeline with computed start_seconds, duration, velocity
- `models.py` — Timeline data classes
- `time_index.py` — Efficient O(1) lookup of active notes at any given frame time

### Rendering (`rendering/`)
**Visual rendering: keyboard, falling notes, effects, colors**

Files:
- `layout.py` — Layout calculations: keyboard position, note fall distance, lookahead region, frame dimensions
- `keyboard.py` — KeyboardRenderer: draws keyboard with key colors, active key glow, key depression
- `notes.py` — FallingNotesRenderer: draws falling note bars with per-note color cache, glow, glitter, guide lines
- `colors.py` — ColorScheme: color mode logic (single, rainbow, neon, part, key_type)
- `themes.py` — THEMES dict, auto_select_theme() based on key signature + tempo
- `effects/` — Visual effects subpackage (see below)

### Effects (`rendering/effects/`)
**Visual effects: particles, bursts, ambient**

Files:
- `__init__.py` — VisualEffects orchestrator class
- `ambient.py` — Starflow background stars, ascending bubbles, note glow
- `particles.py` — Generic particle system used by bursts and comet
- `burst.py` — Neon burst water droplet splash effect

### Export (`export/`)
**Video and audio output**

Files:
- `video_writer.py` — VideoWriter: writes frames to MP4 via ffmpeg pipe
- `audio.py` — Audio generation via fluidsynth (music21 synthesis) or external file; audio-video mux

### Utils (`utils/`)
**Helper utilities**

Files:
- `piano_keys.py` — Keyboard layout constants (MIDI note ranges, white/black key positions, octave info)

### Web (`web/`)
**Flask web UI**

Files:
- `app.py` — Flask application with file upload, form, web preview (calls VideoGenerator internally)
- Templates and static files (Korean UI labels)

## Configuration Flow

```
CLI args (parse_args)
    ↓
Config.from_cli_and_yaml(args, yaml_file)
    ↓
__main__.py applies flag overrides to config
    ↓
VideoGenerator.generate(config)
```

## Typical Modification Patterns

### Adding a new effect:
1. Create new effect class in `rendering/effects/`
2. Add toggle to Config (config.py)
3. Add CLI flag to cli.py
4. Call effect in render_frame() (core/renderer.py)
5. Test with standard test command

### Adding a new color mode:
1. Update ColorScheme in colors.py
2. Add to cli.py color-mode choices
3. Implement color logic in ColorScheme methods
4. Test with --color-mode flag

### Changing video output behavior:
1. Modify Config defaults in config.py
2. Update VideoGenerator.generate() or render_frame()
3. Add CLI args to cli.py if needed
4. Test with test-scores

## Parent Modules

See `/Users/lee/projects/piano-falling-notes/AGENTS.md` for root project structure.
