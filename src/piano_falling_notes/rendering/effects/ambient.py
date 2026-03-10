"""Ambient and overlay effects — note glow, wave ripple, pedal glow, starflow."""

import math

import numpy as np
from PIL import Image


class AmbientEffectsMixin:
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

    def apply_pedal_glow(
        self,
        img: Image.Image,
        keyboard_top: int,
        width: int,
    ) -> Image.Image:
        """Render a subtle warm glow bar at the bottom of the note area when sustain pedal is active."""
        glow_height = 12
        strip_top = max(0, keyboard_top - glow_height)
        strip_bottom = keyboard_top

        arr = np.array(img)
        strip = arr[strip_top:strip_bottom].astype(np.float32)
        h = strip_bottom - strip_top

        # Warm amber glow color
        pedal_color = np.array([255, 180, 60], dtype=np.float32)

        # Vertical fade: stronger at bottom (keyboard line), fading up
        fade_v = np.linspace(0.0, 0.35, h).reshape(h, 1, 1)

        # Apply glow across full width
        glow = np.ones((h, width, 3), dtype=np.float32) * pedal_color * fade_v
        strip = np.minimum(strip + glow, 255.0)

        arr[strip_top:strip_bottom] = strip.astype(np.uint8)
        return Image.fromarray(arr)

    def apply_starflow(
        self,
        img: Image.Image,
        active_keys: dict,      # {midi: velocity}, used to boost nearby stars
        key_map: dict,
        keyboard_top: int,
        color_scheme,
        current_time: float,
    ) -> Image.Image:
        """Ambient starfield that drifts across the background above the keyboard."""
        TARGET_COUNT = 300
        w = img.width
        h_area = max(1, keyboard_top)

        _STAR_COLORS = [
            np.array([180, 240, 255], dtype=np.float32),  # pale cyan
            np.array([220, 220, 255], dtype=np.float32),  # silver-white
            np.array([200, 180, 255], dtype=np.float32),  # pale violet
            np.array([150, 200, 255], dtype=np.float32),  # ice blue
            np.array([255, 220, 255], dtype=np.float32),  # pink-white
            np.array([200, 255, 240], dtype=np.float32),  # mint
            np.array([255, 255, 200], dtype=np.float32),  # warm white
            np.array([180, 180, 255], dtype=np.float32),  # lavender
        ]

        self._star_frame += 1

        # Top up star pool
        while len(self._star_particles) < TARGET_COUNT:
            self._star_particles.append({
                'x': np.random.uniform(-5, w + 5),
                'y': np.random.uniform(0, h_area),
                'vx': np.random.uniform(0.2, 1.8),   # drift right (some fast)
                'vy': np.random.uniform(-0.3, 0.5),  # slight up or down
                'size': np.random.uniform(1.0, 5.5),  # bigger max
                'color': _STAR_COLORS[np.random.randint(0, len(_STAR_COLORS))].copy(),
                'twinkle_phase': np.random.uniform(0, 2 * math.pi),
                'twinkle_freq': np.random.uniform(0.06, 0.22),
            })

        # Active key x-centers for proximity boost
        active_cx = []
        for midi in active_keys:
            key = key_map.get(midi)
            if key is not None:
                active_cx.append(key.x + key.width / 2.0)

        strip_top = 0
        strip_bottom = keyboard_top
        arr = np.array(img)
        overlay = np.zeros((strip_bottom - strip_top, w, 3), dtype=np.float32)

        for p in self._star_particles:
            boost_speed = 1.0
            boost_bright = 1.0
            for acx in active_cx:
                if abs(p['x'] - acx) < 80:
                    boost_speed = 1.3
                    boost_bright = 1.5
                    break

            p['x'] += p['vx'] * boost_speed
            p['y'] += p['vy'] * boost_speed

            # Wrap-around edges
            if p['x'] > w + 10:
                p['x'] = -5.0
                p['y'] = np.random.uniform(0, h_area)
            elif p['x'] < -10:
                p['x'] = float(w) + 5.0
                p['y'] = np.random.uniform(0, h_area)
            if p['y'] > h_area:
                p['y'] = 0.0
                p['x'] = np.random.uniform(0, w)

            # Twinkle alpha — brighter range
            alpha = 0.5 + 0.45 * math.sin(p['twinkle_phase'] + self._star_frame * p['twinkle_freq'])
            alpha = float(np.clip(alpha * boost_bright * 0.85, 0.0, 1.0))

            px = p['x']
            py = p['y']
            size = p['size']
            local_y = py  # strip_top == 0

            if local_y + size < 0 or local_y - size >= strip_bottom:
                continue
            if px + size < 0 or px - size >= w:
                continue

            r = int(math.ceil(size)) + 1
            y0 = int(local_y) - r
            y1 = int(local_y) + r + 1
            x0 = int(px) - r
            x1 = int(px) + r + 1
            oy0 = max(0, y0)
            oy1 = min(overlay.shape[0], y1)
            ox0 = max(0, x0)
            ox1 = min(overlay.shape[1], x1)
            if oy0 >= oy1 or ox0 >= ox1:
                continue

            ys = np.arange(oy0, oy1, dtype=np.float32) - local_y
            xs = np.arange(ox0, ox1, dtype=np.float32) - px
            dist2 = ys[:, np.newaxis] ** 2 + xs[np.newaxis, :] ** 2
            sigma2 = max((size * 0.5) ** 2, 0.5)
            body = np.exp(-dist2 / (2 * sigma2)) * alpha
            overlay[oy0:oy1, ox0:ox1, :] += body[:, :, np.newaxis] * p['color'][np.newaxis, np.newaxis, :]

        if overlay.max() > 0:
            strip = arr[strip_top:strip_bottom].astype(np.float32)
            arr[strip_top:strip_bottom] = np.minimum(strip + overlay, 255.0).astype(np.uint8)

        return Image.fromarray(arr)
