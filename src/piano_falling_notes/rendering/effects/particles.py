"""Particle-based effects — ascending bubbles and comet rise."""

import math

import numpy as np
from PIL import Image


class ParticleEffectsMixin:
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

    def apply_c_note_rise(
        self,
        img: Image.Image,
        newly_active: dict,   # {midi: velocity} of newly struck notes
        active_keys: dict,    # {midi: velocity} currently playing
        key_map: dict,
        keyboard_top: int,
        color_scheme,
        current_time: float,
    ) -> Image.Image:
        """Randomly spawn a glowing comet dot from a currently-active key,
        every 3–5 seconds, rising to screen top along a sine-wave path with tail.
        """
        _ALL_COLORS = [
            (np.array([255, 140, 20],  dtype=np.float32), np.array([255, 230, 180], dtype=np.float32)),  # orange
            (np.array([255, 40,  100], dtype=np.float32), np.array([255, 200, 220], dtype=np.float32)),  # hot pink
            (np.array([80,  200, 255], dtype=np.float32), np.array([200, 240, 255], dtype=np.float32)),  # cyan
            (np.array([180, 80,  255], dtype=np.float32), np.array([230, 200, 255], dtype=np.float32)),  # purple
            (np.array([80,  255, 140], dtype=np.float32), np.array([200, 255, 220], dtype=np.float32)),  # mint
            (np.array([255, 220, 40],  dtype=np.float32), np.array([255, 250, 200], dtype=np.float32)),  # yellow
        ]
        _CORE_COLOR = self._current_comet_core
        TRAIL_LEN = 25

        # Time-based trigger: every 1–3 seconds, from a currently-active note
        if current_time >= self._next_rise_time and active_keys:
            candidates = [m for m in active_keys if key_map.get(m) is not None]
            if candidates:
                # Cycle color every 3-4 comets
                if self._rise_count >= self._next_color_change:
                    idx = np.random.randint(0, len(_ALL_COLORS))
                    self._current_comet_color = _ALL_COLORS[idx][0].copy()
                    self._current_comet_core  = _ALL_COLORS[idx][1].copy()
                    self._next_color_change = self._rise_count + int(np.random.uniform(3, 5))

                midi = int(np.random.choice(candidates))
                key = key_map[midi]
                cx = float(key.x + key.width / 2.0)
                self._firefly_particles.append({
                    'cx': cx,
                    'x': cx,
                    'y': float(keyboard_top),
                    'rise_speed': np.random.uniform(3.5, 5.0),
                    'size': np.random.uniform(6.0, 12.0),
                    'color': self._current_comet_color.copy(),
                    'life': 0,
                    # Irregular path: 3 independent oscillators (sin, cos, tan)
                    'pa1': np.random.uniform(40, 65),   'pf1': np.random.uniform(0.07, 0.13),  'pp1': np.random.uniform(0, 6.28),
                    'pa2': np.random.uniform(25, 45),   'pf2': np.random.uniform(0.14, 0.22),  'pp2': np.random.uniform(0, 6.28),
                    'pa3': np.random.uniform(10, 25),   'pf3': np.random.uniform(0.03, 0.07),  'pp3': np.random.uniform(0, 6.28),
                    'trail': [],
                    'done': False,
                })
                self._rise_count += 1
                self._next_rise_time = current_time + np.random.uniform(1.0, 3.0)

        if not self._firefly_particles and not self._sparkle_dust:
            return img

        arr = np.array(img)
        overlay = np.zeros((keyboard_top, img.width, 3), dtype=np.float32)

        def _draw_star(cx, cy, size, color, alpha):
            """4-pointed star via 4 rotated elongated gaussians + circular core."""
            sigma_long = max(size * 0.55, 1.0)
            sigma_short = max(size * 0.08, 0.2)
            sigma_core = max(size * 0.35, 0.5)
            r = int(math.ceil(sigma_long * 3.5)) + 1
            oy0 = max(0, int(cy) - r)
            oy1 = min(overlay.shape[0], int(cy) + r + 1)
            ox0 = max(0, int(cx) - r)
            ox1 = min(overlay.shape[1], int(cx) + r + 1)
            if oy0 >= oy1 or ox0 >= ox1:
                return
            ys = np.arange(oy0, oy1, dtype=np.float32) - cy
            xs = np.arange(ox0, ox1, dtype=np.float32) - cx
            dy = ys[:, np.newaxis]
            dx = xs[np.newaxis, :]
            star = np.zeros((oy1 - oy0, ox1 - ox0), dtype=np.float32)
            for angle_deg in [0, 45, 90, 135]:
                rad = math.radians(angle_deg)
                ca, sa = math.cos(rad), math.sin(rad)
                xr = dx * ca + dy * sa
                yr = -dx * sa + dy * ca
                spike = np.exp(-(xr ** 2 / (2 * sigma_long ** 2) + yr ** 2 / (2 * sigma_short ** 2)))
                star = np.maximum(star, spike)
            # central core
            dist2 = dy ** 2 + dx ** 2
            core = np.exp(-dist2 / (2 * sigma_core ** 2))
            star = np.maximum(star, core)
            overlay[oy0:oy1, ox0:ox1, :] += (
                (star * alpha)[:, :, np.newaxis] * color[np.newaxis, np.newaxis, :]
            )

        # --- Update and render sparkle dust ---
        alive_dust = []
        for s in self._sparkle_dust:
            s['life'] += 1
            if s['life'] > s['max_life']:
                continue
            s['x'] += s['vx']
            s['y'] += s['vy']
            sx, sy = s['x'], s['y']
            if sy < 0 or sy >= keyboard_top or sx < 0 or sx >= img.width:
                continue
            alive_dust.append(s)
            frac = s['life'] / s['max_life']
            s_alpha = (1.0 - frac) * 0.9
            sigma_s = max(s['size'] * 0.55, 0.3)
            r_s = max(1, int(math.ceil(sigma_s * 3)))
            oy0 = max(0, int(sy) - r_s)
            oy1 = min(overlay.shape[0], int(sy) + r_s + 1)
            ox0 = max(0, int(sx) - r_s)
            ox1 = min(overlay.shape[1], int(sx) + r_s + 1)
            if oy0 >= oy1 or ox0 >= ox1:
                continue
            ys2 = np.arange(oy0, oy1, dtype=np.float32) - sy
            xs2 = np.arange(ox0, ox1, dtype=np.float32) - sx
            dist2 = ys2[:, np.newaxis] ** 2 + xs2[np.newaxis, :] ** 2
            body = np.exp(-dist2 / (2 * sigma_s ** 2)) * s_alpha
            overlay[oy0:oy1, ox0:ox1, :] += (
                body[:, :, np.newaxis] * s['color'][np.newaxis, np.newaxis, :]
            )
        self._sparkle_dust = alive_dust

        # --- Update and render main comets ---
        alive = []
        for p in self._firefly_particles:
            if p['done']:
                continue

            # Record position before moving (for trail)
            p['trail'].append((p['x'], p['y']))
            if len(p['trail']) > TRAIL_LEN:
                p['trail'].pop(0)

            p['life'] += 1
            p['y'] -= p['rise_speed']
            t = p['life']
            tan_val = math.tan(p['pp3'] + t * p['pf3'])
            tan_clamped = max(-2.0, min(2.0, tan_val))
            p['x'] = (p['cx']
                      + p['pa1'] * math.sin(p['pp1'] + t * p['pf1'])
                      + p['pa2'] * math.cos(p['pp2'] + t * p['pf2'])
                      + p['pa3'] * tan_clamped)

            py = p['y']
            px = p['x']
            size = p['size']

            if py + size < 0:
                p['done'] = True
                continue

            alpha = min(1.0, p['life'] / 3.0)
            alive.append(p)

            # Spawn sparkle dust along recent trail
            if len(p['trail']) >= 2:
                for tx, ty in p['trail'][-14:]:
                    if np.random.random() < 0.35:
                        self._sparkle_dust.append({
                            'x': tx + np.random.uniform(-size * 1.5, size * 1.5),
                            'y': ty + np.random.uniform(-size * 0.5, size * 0.5),
                            'vx': np.random.uniform(-0.6, 0.6),
                            'vy': np.random.uniform(0.3, 1.0),   # drift downward
                            'size': np.random.uniform(0.8, 2.5),
                            'color': p['color'].copy(),
                            'life': 0,
                            'max_life': np.random.randint(6, 12),
                        })

            # --- Draw comet tail ---
            trail = p['trail']
            n_trail = len(trail)
            for i, (tx, ty) in enumerate(trail):
                frac = (i + 1) / max(n_trail, 1)
                t_alpha = alpha * frac * 0.55
                t_size = max(size * frac * 0.65, 0.5)
                if ty < 0 or ty >= keyboard_top:
                    continue
                sigma_t = max(t_size * 0.6, 0.4)
                r_t = int(math.ceil(sigma_t * 3.0)) + 1
                oy0 = max(0, int(ty) - r_t)
                oy1 = min(overlay.shape[0], int(ty) + r_t + 1)
                ox0 = max(0, int(tx) - r_t)
                ox1 = min(overlay.shape[1], int(tx) + r_t + 1)
                if oy0 >= oy1 or ox0 >= ox1:
                    continue
                ys = np.arange(oy0, oy1, dtype=np.float32) - ty
                xs = np.arange(ox0, ox1, dtype=np.float32) - tx
                dist2 = ys[:, np.newaxis] ** 2 + xs[np.newaxis, :] ** 2
                body = np.exp(-dist2 / (2 * sigma_t ** 2)) * t_alpha
                overlay[oy0:oy1, ox0:ox1, :] += (
                    body[:, :, np.newaxis] * p['color'][np.newaxis, np.newaxis, :]
                )

            # --- Draw star-shaped head (red spikes) ---
            _draw_star(px, py, size, p['color'], alpha)
            # Inner bright core on top
            _draw_star(px, py, size * 0.3, self._current_comet_core, alpha * 0.9)

        # Feed trail glow points from alive comets
        if hasattr(self, '_comet_trail_glow_enabled') and self._comet_trail_glow_enabled:
            for p in alive:
                if len(p['trail']) >= 3:
                    for tx, ty in p['trail'][-3:]:
                        if 0 <= ty < keyboard_top:
                            self._trail_glow_points.append({
                                'x': tx, 'y': ty,
                                'color': p['color'].copy(),
                                'life': 0,
                                'max_life': 60,  # ~1s at 60fps, ~2s at 30fps
                            })

        self._firefly_particles = alive

        if overlay.max() > 0:
            strip = arr[:keyboard_top].astype(np.float32)
            arr[:keyboard_top] = np.minimum(strip + overlay, 255.0).astype(np.uint8)

        return Image.fromarray(arr)

    def apply_comet_trail_glow(
        self,
        img: Image.Image,
        keyboard_top: int,
    ) -> Image.Image:
        """Render lingering glow points left behind by comets."""
        if not self._trail_glow_points:
            return img

        arr = np.array(img)
        overlay = np.zeros((keyboard_top, img.width, 3), dtype=np.float32)

        alive = []
        for p in self._trail_glow_points:
            p['life'] += 1
            if p['life'] > p['max_life']:
                continue

            px, py = p['x'], p['y']
            if py < 0 or py >= keyboard_top or px < 0 or px >= img.width:
                continue

            alive.append(p)

            # Alpha decays linearly over lifetime
            frac = p['life'] / p['max_life']
            alpha = (1.0 - frac) * 0.4  # max alpha 0.4 for subtlety

            # Gaussian glow dot
            sigma = 8.0
            r = int(math.ceil(sigma * 2.5)) + 1
            oy0 = max(0, int(py) - r)
            oy1 = min(overlay.shape[0], int(py) + r + 1)
            ox0 = max(0, int(px) - r)
            ox1 = min(overlay.shape[1], int(px) + r + 1)
            if oy0 >= oy1 or ox0 >= ox1:
                continue

            ys = np.arange(oy0, oy1, dtype=np.float32) - py
            xs = np.arange(ox0, ox1, dtype=np.float32) - px
            dist2 = ys[:, np.newaxis] ** 2 + xs[np.newaxis, :] ** 2
            body = np.exp(-dist2 / (2 * sigma ** 2)) * alpha
            overlay[oy0:oy1, ox0:ox1, :] += (
                body[:, :, np.newaxis] * p['color'][np.newaxis, np.newaxis, :]
            )

        self._trail_glow_points = alive

        if overlay.max() > 0:
            strip = arr[:keyboard_top].astype(np.float32)
            arr[:keyboard_top] = np.minimum(strip + overlay, 255.0).astype(np.uint8)

        return Image.fromarray(arr)
