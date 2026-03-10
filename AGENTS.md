# AGENTS.md - piano-falling-notes (Root)

Piano Falling Notes is a MusicXML/MIDI to falling notes video generator (PianiCast style).

## Quick Start

```bash
# Install
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Test
.venv/bin/python -m piano_falling_notes test-scores/Golden.mxl -o result/test.mp4 \
  --width 1280 --height 720 --fps 30 --no-audio --color-mode key_type

# Web UI
.venv/bin/python -m piano_falling_notes --web --port 5000
```

## Project Structure

**Root files:**
- `pyproject.toml` — Project metadata, dependencies (music21, Pillow, numpy, tqdm, PyYAML), Python 3.10+ requirement
- `.gitignore` — Standard Python ignore rules
- `CHANGELOG.md`, `DESIGN.md` — Documentation and design notes

**Directories:**
- `src/piano_falling_notes/` — Main package (see nested AGENTS.md)
- `config/` — YAML theme configs and soundfont (default.yaml, TimGM6mb.sf2)
- `docs/` — User-facing documentation (CHANGELOG.md, DESIGN.md)
- `test-scores/` — Test MusicXML files (Golden.mxl, IRIS OUT.mxl, 꿈의 버스.mxl)
- `result/` — Output directory for generated videos (gitignored)

## Key Concepts

### Workflow
1. **Parse**: MusicXML/MIDI → note list + metadata
2. **Timeline**: Build renderer-ready timeline with start_seconds, duration, velocity
3. **Theme**: Auto-select or user-specify theme (classic, midnight, sunset, ocean, neon, pastel)
4. **Layout**: Calculate keyboard position, note fall distance, lookahead region
5. **Render loop**: Per-frame pipeline renders keyboard, falling notes, effects, combines with audio
6. **Export**: MP4 via ffmpeg with optional audio mux

### Color Modes
- `single`: All notes one color (configurable via --note-color)
- `key_type`: White keys vs black keys different colors (--white-key-color, --black-key-color)
- `rainbow`: Per-note cycling through spectrum
- `neon`: Palette-based vibrant colors
- `part`: Different colors for different staves/parts

### Effects
- **Energy color**: Dynamic note color based on 4s density+velocity sliding window (blue→green→orange/red)
- **Neon burst**: Water droplet splash on key strike (height 480px, speeds 90–220px)
- **Comet effect**: Star-shaped shooting stars every 1–3s from active keys (color cycling, sparkle dust trail)
- **Starflow**: Ambient cool-palette star particles drifting background
- **Glow**: Pearlescent glow above keyboard for active notes
- **Guide lines**: Octave-aligned horizontal lines across falling region
- **Glitter**: Twinkling on note bars
- **Key depression**: Visual press animation on keyboard

### Configuration
- CLI flags override defaults and YAML config
- Theme selects background color palette
- Custom background color, background image, or soundfont path
- Video dimensions, fps, crf (quality), lookahead window, keyboard height ratio
- Per-effect toggles (--no-glow, --no-comet, --no-energy-color, --no-starflow, --no-neon-burst, --no-guide-lines)

## AI Agent Instructions

### When modifying this project:

1. **Always run tests against test-scores** before committing:
   ```bash
   .venv/bin/python -m piano_falling_notes test-scores/Golden.mxl -o result/Golden_test.mp4 \
     --width 1280 --height 720 --fps 30 --no-audio --color-mode key_type
   ```

2. **Check config.py** for all user-facing settings before adding new features.

3. **Rendering pipeline is in src/piano_falling_notes/core/generator.py** — this is the orchestrator that ties parser → timeline → rendering → export together.

4. **Web UI is Flask-based** at `src/piano_falling_notes/web/app.py` with Korean labels in templates.

5. **No external dependencies beyond pyproject.toml** — verify any new imports are listed there.

6. **Korean UI labels** in web templates (preserve them; do not translate to English).

7. **Energy-based color system** is pre-computed in generator before render loop (see core/renderer.py::compute_energy_profile).

8. **Per-note color caching** in FallingNotesRenderer._note_color_cache — colors are assigned once on first render.

## CI / Testing

- Standard pytest framework (dev dependency)
- No automated CI configured; manual test video generation is the primary validation
- Test scores in `test-scores/` are golden references

## Deployment

- Package is installable via `pip install -e .`
- CLI entry point: `piano-falling-notes` command (defined in pyproject.toml)
- Web mode runs Flask dev server (not production-ready; use WSGI for production)

## Child Modules

See `/Users/lee/projects/piano-falling-notes/src/piano_falling_notes/AGENTS.md` for package structure.
See `/Users/lee/projects/piano-falling-notes/src/piano_falling_notes/core/AGENTS.md` for core rendering pipeline.
