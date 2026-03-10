"""Impact/burst effects — neon burst water droplet splash."""

import numpy as np
from PIL import Image


class BurstEffectsMixin:
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
            speeds = np.random.uniform(90, 220, num_drops)
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

        splash_height = 480
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
