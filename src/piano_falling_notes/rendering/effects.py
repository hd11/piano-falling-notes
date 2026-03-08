"""Visual effects - optimized for performance."""

import numpy as np
from PIL import Image


class VisualEffects:
    def apply_note_glow(
        self,
        img: Image.Image,
        active_keys: dict,
        key_map: dict,
        keyboard_top: int,
        color_scheme,
        current_time: float,
    ) -> Image.Image:
        """Apply pearlescent glow above keyboard for active notes, matching bubble aesthetic."""
        if not active_keys:
            return img

        import math

        # Work on a narrow strip above the keyboard
        glow_height = 50
        strip_top = max(0, keyboard_top - glow_height)
        strip_bottom = keyboard_top

        arr = np.array(img)
        strip = arr[strip_top:strip_bottom].astype(np.float32)
        h = strip_bottom - strip_top
        w = img.width

        for midi, velocity in active_keys.items():
            key = key_map.get(midi)
            if key is None:
                continue
            color = color_scheme.note_color_rgb(midi, velocity)
            c = np.array(color, dtype=np.float32)
            intensity = (0.5 + velocity * 0.5) * 0.5

            # Glow region x bounds (slightly wider than key)
            margin = max(8, int(key.width * 0.5))
            x0 = max(0, int(key.x - margin))
            x1 = min(w, int(key.x + key.width + margin))
            key_cx = key.x + key.width / 2.0

            # Create vertical fade: strong at bottom (keyboard), fading up
            fade_v = np.linspace(0, 1.0, h).reshape(h, 1)

            # Horizontal gaussian centered on key
            xs = np.arange(x0, x1, dtype=np.float32)
            sigma_x = max(key.width * 0.6, 8.0)
            fade_h = np.exp(-((xs - key_cx) ** 2) / (2 * sigma_x ** 2)).reshape(1, x1 - x0)

            # Combined fade: 2D gaussian-ish glow
            fade = fade_v * fade_h * intensity

            # Pearlescent: blend toward white at center
            white = np.array([255, 255, 255], dtype=np.float32)
            pearl_color = c * 0.6 + white * 0.4

            # Shimmer: subtle time-varying brightness
            shimmer = 0.85 + 0.15 * math.sin(current_time * 4.0 + midi * 0.7)

            glow_color = pearl_color * shimmer
            glow_layer = fade[:, :, np.newaxis] * glow_color[np.newaxis, np.newaxis, :]

            # Additive blend
            region = strip[:, x0:x1, :]
            strip[:, x0:x1, :] = np.minimum(region + glow_layer, 255.0)

        strip = np.clip(strip, 0, 255).astype(np.uint8)
        arr[strip_top:strip_bottom] = strip
        return Image.fromarray(arr)

    def __init__(self):
        self._burst_state = {}  # {midi: {color, intensity, cx, key_w, ray_angles, ray_lengths, frame}}
        self._wave_phase = 0.0  # persistent wave phase counter
        self._bubble_particles = []  # list of particle dicts

    def apply_wave_ripple(
        self,
        img: Image.Image,
        active_keys: dict,
        key_map: dict,
        keyboard_top: int,
        color_scheme,
    ) -> Image.Image:
        """Ambient ocean wave ripple along the keyboard top, enhanced when notes are active."""
        wave_height = 8  # max displacement in pixels
        strip_h = wave_height * 5  # work area
        strip_top = max(0, keyboard_top - strip_h)
        strip_bottom = keyboard_top + 2

        arr = np.array(img)
        strip = arr[strip_top:strip_bottom].astype(np.float32)
        h = strip.shape[0]
        w = img.width

        x_coords = np.arange(w, dtype=np.float32)

        if not active_keys:
            # Ambient ocean wave: slow, graceful sine across full width
            self._wave_phase += 0.06
            wave = np.sin(x_coords * 0.015 - self._wave_phase * 1.5) * 0.5
            avg_color = np.array([100, 140, 200], dtype=np.float32)
        else:
            # Advance phase based on number of active keys
            self._wave_phase += 0.08 + len(active_keys) * 0.01

            # Ambient base layer always present beneath note waves
            wave = np.sin(x_coords * 0.015 - self._wave_phase * 1.5) * 0.3

            # Blend note-colored ripples on top of ambient base
            for midi, velocity in active_keys.items():
                key = key_map.get(midi)
                if key is None:
                    continue
                kcx = key.x + key.width / 2.0

                dist = np.abs(x_coords - kcx)
                freq = 0.04  # wave frequency
                amp = velocity * 0.4  # amplitude tied to velocity
                dampen = np.exp(-dist / 200.0)
                wave += np.sin(dist * freq - self._wave_phase * 3.0) * amp * dampen

            # Average color from active keys, blended with ambient blue
            avg_color = np.zeros(3, dtype=np.float32)
            for midi, velocity in active_keys.items():
                c = color_scheme.note_color_rgb(midi, velocity)
                avg_color += np.array(c, dtype=np.float32) * velocity
            avg_color = avg_color / max(sum(active_keys.values()), 1)
            ambient = np.array([100, 140, 200], dtype=np.float32)
            avg_color = avg_color * 0.7 + ambient * 0.3
            # Brighten
            mc = avg_color.max()
            if mc > 0:
                avg_color = avg_color * (200.0 / mc)

        # Normalize wave to pixel displacement
        wave_max = max(np.abs(wave).max(), 1.0)
        wave_norm = wave / wave_max * wave_height

        # Draw the wave as a bright line along keyboard_top with displacement
        keyboard_row = keyboard_top - strip_top  # row index in strip

        for x in range(w):
            dy = wave_norm[x]
            y_center = keyboard_row + int(dy)
            # Draw 5px thick wave line with glow (offsets -2 to +2)
            for offset in range(-2, 3):
                yy = y_center + offset
                if 0 <= yy < h:
                    dist_factor = 1.0 - abs(offset) / 3.0
                    brightness = dist_factor * 0.7
                    old = strip[yy, x, :]
                    strip[yy, x, :] = np.minimum(
                        old + avg_color * brightness, 255.0
                    )

        strip = np.clip(strip, 0, 255).astype(np.uint8)
        arr[strip_top:strip_bottom] = strip
        return Image.fromarray(arr)

    def apply_neon_burst(
        self,
        img: Image.Image,
        newly_active: dict,
        key_map: dict,
        keyboard_top: int,
        color_scheme,
    ) -> Image.Image:
        """Water droplet splash effect when keys are struck."""
        for midi, velocity in newly_active.items():
            key = key_map.get(midi)
            if key is None:
                continue
            color = color_scheme.note_color_rgb(midi, velocity)
            c = np.array(color, dtype=np.float32)
            max_c = c.max()
            if max_c > 0:
                c = c * (255.0 / max_c)
            intensity = 0.7 + velocity * 0.3
            cx = key.x + key.width / 2.0
            key_w = key.width
            # Generate splash droplets (small arcing particles)
            num_drops = np.random.randint(8, 16)
            # Angles: mostly upward with some spread (-160 to -20 degrees)
            angles = np.random.uniform(-2.7, -0.35, num_drops)
            # Speeds vary for natural look
            speeds = np.random.uniform(50, 130, num_drops)
            # Droplet sizes (radius in pixels)
            sizes = np.random.uniform(2.0, 5.5, num_drops)
            self._burst_state[midi] = {
                'color': c,
                'intensity': intensity,
                'cx': cx,
                'key_w': key_w,
                'angles': angles,
                'speeds': speeds,
                'sizes': sizes,
                'frame': 0,
            }

        if not self._burst_state:
            return img

        splash_height = 260
        strip_top = max(0, keyboard_top - splash_height)
        strip_bottom = keyboard_top

        arr = np.array(img)
        strip = arr[strip_top:strip_bottom].astype(np.float32)
        h = strip_bottom - strip_top
        w = img.width

        expired = []
        for midi, state in self._burst_state.items():
            c = state['color']
            intensity = state['intensity']
            cx = state['cx']
            key_w = state['key_w']
            frame = state['frame']

            # Overall fade
            fade = intensity * (0.75 ** frame)
            if fade < 0.01:
                expired.append(midi)
                continue

            # === Layer 1: Central splash ring (expanding water ring) ===
            ring_r = key_w * (0.8 + frame * 1.0)
            if ring_r < key_w * 8:
                ring_thick = 0.2 - frame * 0.03
                ring_thick = max(ring_thick, 0.05)
                rx0 = max(0, int(cx - ring_r * 1.5))
                rx1 = min(w, int(cx + ring_r * 1.5))
                if rx0 < rx1:
                    cols = np.arange(rx0, rx1, dtype=np.float32)
                    rows = np.arange(h, dtype=np.float32)
                    dx = (cols - cx) / max(ring_r, 1)
                    dy = (rows - float(h)) / max(ring_r * 0.5, 1)
                    dist = np.sqrt(dy[:, np.newaxis] ** 2 + dx[np.newaxis, :] ** 2)
                    ring = np.exp(-((dist - 1.0) ** 2) / (2 * ring_thick ** 2))
                    ring_light = ring[:, :, np.newaxis] * c[np.newaxis, np.newaxis, :] * fade * 0.5
                    region = strip[:, rx0:rx1, :]
                    strip[:, rx0:rx1, :] = np.minimum(region + ring_light, 255.0)

            # === Layer 2: Small central glow (impact point) ===
            if frame <= 3:
                glow_r = key_w * (1.2 - frame * 0.3)
                gx0 = max(0, int(cx - glow_r * 2))
                gx1 = min(w, int(cx + glow_r * 2))
                if gx0 < gx1:
                    cols = np.arange(gx0, gx1, dtype=np.float32)
                    rows = np.arange(h, dtype=np.float32)
                    dx = (cols - cx) / max(glow_r, 1)
                    dy = (rows - float(h)) / max(glow_r * 0.6, 1)
                    dist2 = dy[:, np.newaxis] ** 2 + dx[np.newaxis, :] ** 2
                    glow = np.exp(-dist2 / (2 * 0.3 ** 2)) * fade * 0.8
                    white = np.array([255, 255, 255], dtype=np.float32)
                    wmix = np.exp(-dist2 / (2 * 0.15 ** 2))
                    glow_color = wmix[:, :, np.newaxis] * white + (1 - wmix[:, :, np.newaxis]) * c
                    glow_light = glow[:, :, np.newaxis] * glow_color
                    region = strip[:, gx0:gx1, :]
                    strip[:, gx0:gx1, :] = np.minimum(region + glow_light, 255.0)

            # === Layer 3: Flying droplets ===
            if frame <= 10:
                angles = state['angles']
                speeds = state['speeds']
                sizes = state['sizes']
                gravity = 3.0  # pixels per frame^2 downward
                t = frame + 0.5  # time factor

                for angle, speed, drop_size in zip(angles, speeds, sizes):
                    # Parabolic trajectory (gravity pulls droplets down)
                    dx_pos = np.cos(angle) * speed * t * 0.3
                    dy_pos = np.sin(angle) * speed * t * 0.3 + 0.5 * gravity * t * t
                    drop_x = int(cx + dx_pos)
                    drop_y = int(h + dy_pos)

                    if drop_y < 0 or drop_y >= h or drop_x < 0 or drop_x >= w:
                        continue

                    # Draw circular droplet
                    r = max(1, int(drop_size * (1.0 - frame * 0.1)))
                    dy_range = range(max(0, drop_y - r), min(h, drop_y + r + 1))
                    dx_range = range(max(0, drop_x - r), min(w, drop_x + r + 1))

                    drop_brightness = fade * (1.0 - frame * 0.08)
                    # Droplet color: slightly whitened version of note color
                    white = np.array([255, 255, 255], dtype=np.float32)
                    drop_color = c * 0.6 + white * 0.4

                    for yy in dy_range:
                        for xx in dx_range:
                            dist_sq = (yy - drop_y) ** 2 + (xx - drop_x) ** 2
                            if dist_sq <= r * r:
                                falloff = 1.0 - (dist_sq / max(r * r, 1))
                                pixel_color = drop_color * drop_brightness * falloff
                                strip[yy, xx, :] = np.minimum(
                                    strip[yy, xx, :] + pixel_color, 255.0
                                )

            state['frame'] = frame + 1

        for midi in expired:
            self._burst_state.pop(midi, None)

        strip = np.clip(strip, 0, 255).astype(np.uint8)
        arr[strip_top:strip_bottom] = strip
        return Image.fromarray(arr)

    def apply_ascending_bubbles(
        self,
        img: Image.Image,
        visible_notes: list,  # all visible RenderNote objects
        active_keys: dict,    # {midi: velocity} currently playing
        key_map: dict,
        keyboard_top: int,
        color_scheme,
        current_time: float,
    ) -> Image.Image:
        """Falling sparkle particles alongside notes.

        Small luminous particles fall downward alongside the falling notes,
        creating an elegant dreamy pearlescent effect.
        """
        import math

        white = np.array([255, 255, 255], dtype=np.float32)

        # --- Spawn new particles for each active note ---
        for midi, velocity in active_keys.items():
            key = key_map.get(midi)
            if key is None:
                continue
            color = color_scheme.note_color_rgb(midi, velocity)
            # Pearlescent: blend note color toward white
            c = np.array(color, dtype=np.float32)
            white = np.array([255, 255, 255], dtype=np.float32)
            pearl = np.clip(c * 0.55 + white * 0.45, 0, 255)

            num_new = np.random.randint(3, 7)
            key_x = float(key.x)
            key_w = float(key.width)

            for _ in range(num_new):
                # Spawn along left or right edge, near keyboard_top
                side = np.random.choice([-1, 1])
                # x: within ~4px of the left or right edge of the note
                if side < 0:
                    x = key_x + np.random.uniform(0, 4)
                else:
                    x = key_x + key_w - np.random.uniform(0, 4)
                # y: spawn at keyboard top where notes are active
                y = float(keyboard_top) - np.random.uniform(0, 6)
                lifetime = np.random.randint(40, 61)
                size = np.random.uniform(2.0, 5.0)
                # Upward velocity (rising from active notes)
                vy = -np.random.uniform(1.0, 3.0)
                # Slight horizontal drift; will also use a sine wobble
                vx = np.random.uniform(-0.4, 0.4) * float(side)
                # Random phase offset for wobble
                wobble_phase = np.random.uniform(0, 2 * math.pi)
                wobble_amp = np.random.uniform(0.3, 0.8)

                self._bubble_particles.append({
                    'x': x,
                    'y': y,
                    'vx': vx,
                    'vy': vy,
                    'size': size,
                    'color': pearl.copy(),
                    'alpha': 0.0,       # starts invisible, fades in quickly
                    'life': 0,
                    'max_life': lifetime,
                    'wobble_phase': wobble_phase,
                    'wobble_amp': wobble_amp,
                })

        if not self._bubble_particles:
            return img

        # --- Work on a strip above keyboard where particles rise ---
        max_rise = 65 * 3  # generous headroom
        strip_top = max(0, keyboard_top - max_rise)
        strip_bottom = min(img.height, keyboard_top + 4)

        arr = np.array(img)
        # Use float32 overlay for additive blending
        overlay = np.zeros((strip_bottom - strip_top, img.width, 3), dtype=np.float32)
        overlay_alpha = np.zeros((strip_bottom - strip_top, img.width), dtype=np.float32)

        alive = []
        for p in self._bubble_particles:
            p['life'] += 1
            if p['life'] > p['max_life']:
                continue  # expired

            life_frac = p['life'] / p['max_life']

            # Alpha: quick fade-in (0->0.3 in first 8 frames), hold, fade-out
            if p['life'] <= 8:
                alpha = life_frac / (8 / p['max_life'])
            else:
                alpha = 1.0 - life_frac
            alpha = float(np.clip(alpha * 0.85, 0.0, 0.85))

            # Move particle upward with sine wobble
            wobble = math.sin(p['wobble_phase'] + p['life'] * 0.25) * p['wobble_amp']
            p['x'] += p['vx'] + wobble
            p['y'] += p['vy']

            px = p['x']
            py = p['y']
            size = p['size']

            # Skip if outside strip
            if py + size < strip_top or py - size > strip_bottom:
                alive.append(p)
                continue
            if px + size < 0 or px - size > img.width:
                alive.append(p)
                continue

            alive.append(p)

            # Draw soft circle with gaussian falloff using numpy
            r = int(math.ceil(size)) + 1
            local_y = py - strip_top
            local_x = px

            y0 = int(local_y) - r
            y1 = int(local_y) + r + 1
            x0 = int(local_x) - r
            x1 = int(local_x) + r + 1

            # Clip to overlay bounds
            oy0 = max(0, y0)
            oy1 = min(overlay.shape[0], y1)
            ox0 = max(0, x0)
            ox1 = min(overlay.shape[1], x1)

            if oy0 >= oy1 or ox0 >= ox1:
                continue

            # Grid of distances from bubble center
            ys = np.arange(oy0, oy1, dtype=np.float32) - local_y
            xs = np.arange(ox0, ox1, dtype=np.float32) - local_x
            dist2 = ys[:, np.newaxis] ** 2 + xs[np.newaxis, :] ** 2

            # Gaussian falloff for soft bubble body
            sigma2 = (size * 0.5) ** 2
            body = np.exp(-dist2 / (2 * max(sigma2, 0.5))) * alpha

            # Bright inner highlight (white spot at ~30% radius)
            sigma_h2 = (size * 0.2) ** 2
            highlight = np.exp(-dist2 / (2 * max(sigma_h2, 0.1))) * alpha * 0.9

            color_layer = body[:, :, np.newaxis] * p['color'][np.newaxis, np.newaxis, :]
            white_layer = highlight[:, :, np.newaxis] * white[np.newaxis, np.newaxis, :]

            # Additive blend both layers onto overlay
            overlay[oy0:oy1, ox0:ox1, :] += color_layer + white_layer
            overlay_alpha[oy0:oy1, ox0:ox1] = np.maximum(
                overlay_alpha[oy0:oy1, ox0:ox1], body + highlight * 0.5
            )

        self._bubble_particles = alive

        # Composite overlay onto image strip
        if overlay.max() > 0:
            strip = arr[strip_top:strip_bottom].astype(np.float32)
            # Additive blend capped at 255
            blended = np.minimum(strip + overlay, 255.0)
            arr[strip_top:strip_bottom] = blended.astype(np.uint8)

        return Image.fromarray(arr)

    def apply_dj_eq(
        self,
        img: Image.Image,
        active_keys: dict,  # {midi_number: velocity}
        key_map: dict,
        keyboard_top: int,
        color_scheme,
        eq_height: int = 150,  # max height of EQ bars in pixels
    ) -> Image.Image:
        """DJ EQ / equalizer visualization: velocity-driven vertical bars above keyboard."""
        if not active_keys:
            return img

        arr = np.array(img)
        strip_top = max(0, keyboard_top - eq_height)
        strip_bottom = keyboard_top  # bars grow upward from keyboard_top

        h = strip_bottom - strip_top  # full EQ strip height

        strip = arr[strip_top:strip_bottom].astype(np.float32)

        # Pre-build a vertical gradient multiplier: bottom row = 1.0, top row = 0.3
        # strip row 0 is the topmost pixel, row h-1 is just above the keyboard
        grad = np.linspace(0.3, 1.0, h, dtype=np.float32)  # dim at top, bright at bottom

        for midi, velocity in active_keys.items():
            key = key_map.get(midi)
            if key is None:
                continue

            color = color_scheme.note_color_rgb(midi, velocity)
            c = np.array(color, dtype=np.float32)

            # Bar occupies the same x footprint as the note (1 px gap each side)
            x0 = max(0, int(key.x) + 1)
            x1 = min(img.width, int(key.x + key.width) - 1)
            if x0 >= x1:
                continue

            # Bar height proportional to velocity (0–1 float assumed by convention)
            bar_px = max(1, int(velocity * eq_height))
            bar_px = min(bar_px, h)

            # Rows in strip that the bar occupies: bottom-aligned
            bar_row_start = h - bar_px   # strip index of bar top
            bar_row_end = h              # strip index past bar bottom

            # Gradient slice for this bar (subset of full grad)
            bar_grad = grad[bar_row_start:bar_row_end]  # shape (bar_px,)

            # Color columns: shape (bar_px, width, 3)
            bar_color = (
                bar_grad[:, np.newaxis, np.newaxis]
                * c[np.newaxis, np.newaxis, :]
            )  # (bar_px, 1, 3) broadcast to (bar_px, x1-x0, 3) below

            region = strip[bar_row_start:bar_row_end, x0:x1, :]
            # Additive blend capped at 255
            strip[bar_row_start:bar_row_end, x0:x1, :] = np.minimum(
                region + bar_color, 255.0
            )

        strip = np.clip(strip, 0, 255).astype(np.uint8)
        arr[strip_top:strip_bottom] = strip
        return Image.fromarray(arr)
