# Effects Package

Visual effects for piano falling notes — mixin-based architecture.

## Purpose

The effects package provides composable visual enhancements rendered on top of falling notes and keyboard. Effects use additive blending and alpha compositing to layer animations.

## Architecture

**Facade Pattern:** VisualEffects class inherits from 3 mixin classes.

**Mixin Classes:**
- `BurstEffectsMixin` — impact/splash effects on key strikes
- `ParticleEffectsMixin` — particle-based animations (bubbles, comets, sparkles)
- `AmbientEffectsMixin` — background/ambient effects (glow, waves, stars)

Each mixin is stateless except for shared state initialized in VisualEffects.__init__.

## State Initialization

**VisualEffects.__init__** initializes all shared state:

```python
self._burst_state = {}              # {midi: {...}} active bursts
self._wave_phase = 0.0              # persistent wave phase
self._bubble_particles = []         # ascending bubble particles
self._firefly_particles = []        # comet particles
self._rise_cooldown = 0             # frames until next comet
self._next_rise_time = 0.0          # seconds until next comet
self._sparkle_dust = []             # tiny sparkling trail particles
self._rise_count = 0                # total comets spawned
self._next_color_change = int(...)  # comet color cycle counter
self._current_comet_color = ...     # active comet palette color
self._current_comet_core = ...      # active comet bright core
self._star_particles = []           # starfield particles
self._star_frame = 0                # frame counter for twinkling
self._trail_glow_points = []        # lingering comet trail glows
self._comet_trail_glow_enabled = False  # flag set by renderer
```

Mixin methods must assume this state exists.

## Module Reference

### __init__.py

**VisualEffects class**

Inherits from: BurstEffectsMixin, ParticleEffectsMixin, AmbientEffectsMixin

Methods (delegated to mixins):
- `apply_neon_burst(img, newly_active, key_map, keyboard_top, color_scheme)`
- `apply_ascending_bubbles(img, visible_notes, active_keys, key_map, keyboard_top, color_scheme, current_time)`
- `apply_c_note_rise(img, newly_active, active_keys, key_map, keyboard_top, color_scheme, current_time)`
- `apply_comet_trail_glow(img, keyboard_top)`
- `apply_note_glow(img, active_keys, key_map, keyboard_top, color_scheme, current_time)`
- `apply_wave_ripple(img, active_keys, key_map, keyboard_top, color_scheme)`
- `apply_pedal_glow(img, keyboard_top, width)`
- `apply_starflow(img, active_keys, key_map, keyboard_top, color_scheme, current_time)`

### burst.py

**BurstEffectsMixin class**

Requires: VisualEffects.__init__ for _burst_state

#### apply_neon_burst(img, newly_active, key_map, keyboard_top, color_scheme)

Water droplet splash effect on key strikes (newly played notes).

Parameters:
- `newly_active` — {midi: velocity} of notes just struck
- `keyboard_top` — y boundary (bottom of effect area)

Behavior:
- Triggers on each newly_active key
- 480px tall effect zone above keyboard
- 3 effect layers (composited):
  1. Expanding water ring (gaussian ring shape, fades out)
  2. Central glow (bright white core at impact point)
  3. Flying droplets (8–16 droplets, parabolic trajectories with gravity)

Lifecycle:
- Frame 0–3: Central glow active
- Frame 0–10: Flying droplets travel
- Fades over ~15 frames total
- State: _burst_state[midi] tracks frame, color, position, droplets

Rendering:
- Gaussian shape for water ring and central glow
- Circular droplets with soft falloff
- Additive blending (255 clipped)
- Color: note color, intensity modulated by velocity

### particles.py

**ParticleEffectsMixin class**

Requires: VisualEffects.__init__ for bubble/firefly/sparkle state

#### apply_ascending_bubbles(img, visible_notes, active_keys, key_map, keyboard_top, color_scheme, current_time)

Pearlescent particles rising alongside active notes.

Parameters:
- `visible_notes` — all RenderNote objects currently rendering
- `active_keys` — {midi: velocity} currently playing

Behavior:
- Spawns 3–7 particles per frame per active key
- Particles rise upward (vy = -1 to -3 px/frame)
- Spawn position: left/right edge of key, near keyboard_top
- Wobble: sine-wave side-to-side drift
- Lifetime: 40–61 frames
- Color: pearlescent blend (note color 0.55 + white 0.45)

Rendering:
- Work on strip 195px above keyboard
- Gaussian bubble body with inner white highlight
- Additive blending
- Alpha: fade-in first 8 frames, fade-out at end
- Size: 2–5 pixels

State: _bubble_particles list of particle dicts

#### apply_c_note_rise(img, newly_active, active_keys, key_map, keyboard_top, color_scheme, current_time)

Glowing comet effect rising from active keys. Triggers every 1–3 seconds with 6-color palette cycling.

Parameters:
- `active_keys` — {midi: velocity} currently playing (for source selection)
- `current_time` — seconds elapsed

Spawning:
- Time-based: triggers when current_time >= _next_rise_time
- Source: random currently-active key
- Interval: 1–3 seconds (uniform random)
- Color cycle: every 3–4 comets (6 palettes: orange, pink, cyan, purple, mint, yellow)

Comet Properties:
- Rise speed: 3.5–5.0 px/frame
- Size: 6–12 pixels
- Path: irregular (3 independent oscillators — sin, cos, clamped tan)
  - sin: amplitude 40–65, frequency 0.07–0.13
  - cos: amplitude 25–45, frequency 0.14–0.22
  - tan: amplitude 10–25, frequency 0.03–0.07, clamped ±2.0
- Trail: 25 points recorded per frame

Rendering:
- 4-pointed star head (4 rotated elongated gaussians + circular core)
  - Outer spikes: sigma_long = size × 0.55
  - Spike thickness: sigma_short = size × 0.08
  - Core: sigma_core = size × 0.35
- Bright core overlay: size × 0.3
- Tail: 25 trail points, size/alpha gradient from back to head
- Sparkle dust: 14 recent trail points spawn 35% chance per point
  - Tiny particles: 0.8–2.5px, falling (vy +0.3–1.0)
  - Lifetime: 6–12 frames

State: _firefly_particles, _sparkle_dust, _rise_count, _next_rise_time, _current_comet_color, _current_comet_core

#### apply_comet_trail_glow(img, keyboard_top)

Lingering glow points left by comet trails. Subtle background glow effect.

Parameters:
- `keyboard_top` — y boundary

Behavior:
- Populated by apply_c_note_rise when _comet_trail_glow_enabled is True
- Takes last 3 trail points from each active comet
- Glow duration: 60 frames (~1s at 60fps, ~2s at 30fps)
- Fades linearly over lifetime

Rendering:
- Gaussian glow dot (sigma = 8.0)
- Alpha: (1.0 - frac) × 0.4 (max 40%)
- Additive blending

State: _trail_glow_points (fed by apply_c_note_rise), _comet_trail_glow_enabled flag

Gate: set _comet_trail_glow_enabled = True before calling apply_c_note_rise to enable

### ambient.py

**AmbientEffectsMixin class**

Requires: VisualEffects.__init__ for _wave_phase and _star_particles

#### apply_note_glow(img, active_keys, key_map, keyboard_top, color_scheme, current_time)

Pearlescent glow above keyboard for active notes.

Parameters:
- `active_keys` — {midi: velocity} currently playing
- `current_time` — for shimmer effect

Behavior:
- 50px tall strip above keyboard
- Per-key glow: gaussian spread horizontally, linear fade vertically
- Glow intensity: (0.5 + velocity × 0.5) × 0.5
- Shimmer: time-varying brightness (sin wave, midi-dependent phase)
- Color: pearlescent (note color 0.6 + white 0.4)

Rendering:
- Horizontal gaussian centered on key (sigma = key.width × 0.6)
- Vertical linear fade: stronger at bottom (keyboard)
- Additive blending

#### apply_wave_ripple(img, active_keys, key_map, keyboard_top, color_scheme)

Ocean wave ripple along keyboard top boundary. Ambient effect enhanced when notes play.

Behavior:
- Persistent phase counter (_wave_phase)
- Idle state: slow sine wave, ambient blue color
- Active state: note-colored ripples centered on playing keys, phase advances faster
- Wave: smooth sinusoid with damping by distance from active keys
- Color: blends active note colors with ambient blue (70% note + 30% blue)

Rendering:
- Work on 40px tall strip around keyboard_top
- Displacement wave: ±8px
- 5px thick wave line with gaussian falloff
- Additive blending

#### apply_pedal_glow(img, keyboard_top, width)

Subtle warm glow bar when sustain pedal is active (note: called directly when needed, not automatic).

Parameters:
- `width` — screen width

Behavior:
- 12px tall glow above keyboard_top
- Amber color: (255, 180, 60)
- Linear vertical fade: 0 at top, 0.35 at bottom (keyboard)
- Full width horizontal spread

Rendering:
- Simple linear fade + additive blending

#### apply_starflow(img, active_keys, key_map, keyboard_top, color_scheme, current_time)

Ambient starfield drifting across background. 300 stars with proximity boost.

Parameters:
- `active_keys` — {midi: velocity} for nearby star boost
- `current_time` — not directly used (uses internal _star_frame)

Behavior:
- Maintains 300 stars (TARGET_COUNT)
- Stars drift rightward (vx = 0.2–1.8 px/frame)
- Slight vertical drift (vy = -0.3–0.5)
- Proximity boost: if star is <80px from active key, boost speed 1.3x and brightness 1.5x
- Wrap-around edges: recycle stars at left when they exit right

Rendering:
- Gaussian soft circles (size 1–5.5 px)
- 8 cool-palette colors (cyan, silver-white, violet, ice blue, pink-white, mint, warm white, lavender)
- Twinkle alpha: 0.5–0.95 (sine wave, per-star phase offset)
- Additive blending

State: _star_particles, _star_frame (frame counter for tween phase)

## Common Patterns

**Rendering Overlay Pattern**
```python
# Create empty overlay (numpy float32)
overlay = np.zeros((h, w, 3), dtype=np.float32)

# Draw effects onto overlay
# ...
for item in particles:
    # Compute gaussian/shape, multiply by alpha
    # overlay[y0:y1, x0:x1] += shape

# Composite onto image with additive blending
arr = np.array(img)
strip = arr[y_start:y_end].astype(np.float32)
arr[y_start:y_end] = np.minimum(strip + overlay, 255.0).astype(np.uint8)
```

**Gaussian Rendering**
```python
# Distance grid
dist2 = (ys[:, np.newaxis] ** 2) + (xs[np.newaxis, :] ** 2)
# Gaussian shape
body = np.exp(-dist2 / (2 * sigma ** 2)) * alpha
```

**Particle State Pattern**
Each particle stored as dict with keys:
- Position: `x`, `y`
- Velocity: `vx`, `vy`
- Visual: `size`, `color`, `alpha`
- Life: `life`, `max_life`
- Extra: animation parameters (wobble, twinkle phase, etc.)

**Adding a New Effect**
1. Create mixin class in new file `effect_name.py`
2. Implement `apply_effect_name(...)` method
3. Add mixin to VisualEffects inheritance list in `__init__.py`
4. Initialize state in VisualEffects.__init__
5. Add gate flag if effect should be optional (config toggle)
6. Call from renderer loop

## Rendering Rules

**Coordinate System**
- All effects render above keyboard_top only (except burst which works above keyboard)
- y=0 is top, y=keyboard_top is keyboard boundary
- Clipping required for edge cases

**Blending**
- All effects use additive blending (min(src + effect, 255))
- No alpha compositing (fully additive)
- Order: effects render in sequence, each additively composites

**Frame Rate**
- Time-based effects (wave phase, twinkling) use frame counters or current_time
- Particle lifetimes in frame counts (frame += 1 per call)
- At 60fps vs 30fps: trail lengths and timings should adjust
