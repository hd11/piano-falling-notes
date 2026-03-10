"""Shared render pipeline for CLI, web conversion, and web preview."""

from PIL import Image


# Energy -> color palettes (key_type + single modes)
_PAL_LOW = ((80, 130, 255), (160, 80, 255))      # blue / purple   (calm)
_PAL_MID = ((0, 255, 128), (0, 140, 255))         # green / cyan    (neutral)
_PAL_HIGH = ((255, 160, 0), (255, 60, 40))        # orange / red    (energetic)


def _lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def compute_energy_profile(timeline_notes, total_duration):
    """Pre-compute energy profile (note density + velocity over 4s window).

    Returns dict mapping int(seconds) -> float(0-1).
    """
    _ENERGY_WINDOW = 4.0
    _raw_energy = {}
    for _t in range(int(total_duration) + 2):
        _wn = [n for n in timeline_notes if _t <= n.start_seconds < _t + _ENERGY_WINDOW]
        if _wn:
            _density = len(_wn) / _ENERGY_WINDOW
            _avg_vel = sum(n.velocity for n in _wn) / len(_wn)
            _raw_energy[_t] = _density * 0.5 + _avg_vel * 0.5
        else:
            _raw_energy[_t] = 0.0
    # 5-point smoothing
    _smoothed = {_t: sum(_raw_energy.get(_t + d, 0) for d in range(-2, 3)) / 5
                 for _t in _raw_energy}
    # Normalize relative to this song's own range so full palette is always used
    _e_min = min(_smoothed.values()) if _smoothed else 0.0
    _e_max = max(_smoothed.values()) if _smoothed else 1.0
    _e_range = max(_e_max - _e_min, 0.01)
    return {_t: (_v - _e_min) / _e_range for _t, _v in _smoothed.items()}


def apply_energy_color(color_scheme, energy_map, current_time):
    """Apply energy-based color to color_scheme for current_time."""
    _e = energy_map.get(int(current_time), 0.5)
    if _e < 0.60:                          # blue  (0 ~ 0.60 — 60%)
        _wc = _lerp_color(_PAL_LOW[0], _PAL_MID[0], _e / 0.60)
        _bc = _lerp_color(_PAL_LOW[1], _PAL_MID[1], _e / 0.60)
    elif _e < 0.90:                        # green (0.60 ~ 0.90 — 30%)
        _wc = _lerp_color(_PAL_MID[0], _PAL_HIGH[0], (_e - 0.60) / 0.30)
        _bc = _lerp_color(_PAL_MID[1], _PAL_HIGH[1], (_e - 0.60) / 0.30)
    else:                                  # orange/red (0.90 ~ 1.0 — 10%)
        _wc, _bc = _PAL_HIGH
    color_scheme.mode = "key_type"
    color_scheme.white_key_note_color = _wc
    color_scheme.black_key_note_color = _bc


def make_background_frame(layout, config, background_img=None):
    """Create background frame (solid color or image copy)."""
    if background_img is not None:
        return background_img.copy()
    return Image.new('RGB', (layout.width, layout.height), config.background_color)


def render_frame(frame, layout, color_scheme, falling, keyboard, effects,
                 time_index, current_time, config, energy_map, metadata, prev_active):
    """Render a single frame with all effects in correct order.

    Returns (frame, active_starts).
    """
    # 1. Energy-based color update
    if config.energy_color and current_time >= 0 and energy_map:
        apply_energy_color(color_scheme, energy_map, current_time)

    # 2. Query visible notes
    view_start = current_time
    view_end = current_time + layout.lookahead_seconds
    visible = time_index.query(view_start, view_end)

    # 3. Draw falling notes
    frame = falling.render(frame, visible, current_time)

    # 4. Find active/newly_active notes
    active = {}
    active_starts = {}
    for n in visible:
        if n.start_seconds <= current_time < n.start_seconds + n.duration_seconds * config.note_duration_ratio:
            active[n.midi_number] = n.velocity
            active_starts[n.midi_number] = n.start_seconds

    newly_active = {}
    for m, v in active.items():
        if m not in prev_active or active_starts[m] != prev_active[m]:
            newly_active[m] = v

    # 5. Neon burst on key strike
    if config.neon_burst and newly_active:
        frame = effects.apply_neon_burst(frame, newly_active, keyboard.keys, layout.keyboard_top, color_scheme)

    # 6. Ascending bubbles
    frame = effects.apply_ascending_bubbles(frame, visible, active, keyboard.keys, layout.keyboard_top, color_scheme, current_time)

    # 7. Starflow
    if config.starflow:
        frame = effects.apply_starflow(frame, active, keyboard.keys, layout.keyboard_top, color_scheme, current_time)

    # 8. Comet effect
    if config.comet_effect:
        # Set comet trail glow feed flag
        effects._comet_trail_glow_enabled = config.comet_trail_glow
        frame = effects.apply_c_note_rise(frame, newly_active, active, keyboard.keys, layout.keyboard_top, color_scheme, current_time)

    # 8b. Comet trail glow (lingering wake)
    if config.comet_effect and config.comet_trail_glow:
        frame = effects.apply_comet_trail_glow(frame, layout.keyboard_top)

    # 9. Note glow (glow_enabled guard — fixes missing guard bug)
    if config.glow_enabled and active:
        frame = effects.apply_note_glow(frame, active, keyboard.keys, layout.keyboard_top, color_scheme, current_time)

    # 10. Wave ripple
    frame = effects.apply_wave_ripple(frame, active, keyboard.keys, layout.keyboard_top, color_scheme)

    # 11. Pedal visualization
    if config.pedal and metadata.get('pedal_events'):
        pedal_active = any(
            pe['start_seconds'] <= current_time < pe['end_seconds']
            for pe in metadata['pedal_events']
        )
        if pedal_active:
            frame = effects.apply_pedal_glow(frame, layout.keyboard_top, layout.width)

    # 12. Render keyboard
    kb_img = keyboard.render(active)
    frame.paste(kb_img, (0, layout.keyboard_top))

    return frame, active_starts
