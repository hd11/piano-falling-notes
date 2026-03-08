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
    ) -> Image.Image:
        """Apply glow effects using fast numpy blending on a local strip."""
        if not active_keys:
            return img

        # Work on a narrow strip above the keyboard (much faster than full image)
        glow_height = 40
        strip_top = max(0, keyboard_top - glow_height)
        strip_bottom = keyboard_top

        arr = np.array(img)
        strip = arr[strip_top:strip_bottom].astype(np.float32)

        for midi, velocity in active_keys.items():
            key = key_map.get(midi)
            if key is None:
                continue
            color = color_scheme.note_color_rgb(midi, velocity)
            intensity = (0.5 + velocity * 0.5) * 0.6

            # Glow region x bounds (slightly wider than key)
            margin = max(6, int(key.width * 0.4))
            x0 = max(0, int(key.x - margin))
            x1 = min(img.width, int(key.x + key.width + margin))

            # Create vertical fade: strong at bottom (keyboard), fading up
            h = strip_bottom - strip_top
            fade = np.linspace(0, intensity, h).reshape(h, 1, 1)

            # Blend color into strip
            glow_color = np.array(color, dtype=np.float32).reshape(1, 1, 3)
            region = strip[:, x0:x1, :]
            strip[:, x0:x1, :] = region + (glow_color - region) * fade

        strip = np.clip(strip, 0, 255).astype(np.uint8)
        arr[strip_top:strip_bottom] = strip
        return Image.fromarray(arr)

    def apply_neon_burst(
        self,
        img: Image.Image,
        newly_active: dict,  # {midi_number: velocity} — keys that JUST started playing this frame
        key_map: dict,
        keyboard_top: int,
        color_scheme,
    ) -> Image.Image:
        """PianiCast-style neon burst: bright radial flash at key-strike point."""
        if not newly_active:
            return img

        above = 60
        below = 20
        strip_top = max(0, keyboard_top - above)
        strip_bottom = min(img.height, keyboard_top + below)

        arr = np.array(img)
        strip = arr[strip_top:strip_bottom].astype(np.float32)
        h = strip_bottom - strip_top
        # Row indices relative to strip; centre row is at index `above` (keyboard_top row)
        centre_row = keyboard_top - strip_top  # rows 0..h-1

        rows = np.arange(h, dtype=np.float32)

        for midi, velocity in newly_active.items():
            key = key_map.get(midi)
            if key is None:
                continue

            color = color_scheme.note_color_rgb(midi, velocity)
            # Boost to maximum brightness while preserving hue
            c = np.array(color, dtype=np.float32)
            max_c = c.max()
            if max_c > 0:
                c = c * (255.0 / max_c)

            intensity = 0.4 + velocity * 0.6  # 0.4–1.0 range

            cx = key.x + key.width / 2.0
            burst_half_w = key.width  # 2x key width total
            x0 = max(0, int(cx - burst_half_w))
            x1 = min(img.width, int(cx + burst_half_w))
            if x0 >= x1:
                continue

            cols = np.arange(x0, x1, dtype=np.float32)

            # Radial distance from burst centre for each (row, col)
            dy = (rows - centre_row) / max(above, 1)          # shape (h,)
            dx = (cols - cx) / max(burst_half_w, 1)           # shape (x1-x0,)
            # Broadcast to (h, width) grid
            dist2 = dy[:, np.newaxis] ** 2 + dx[np.newaxis, :] ** 2  # (h, w)

            # Gaussian radial falloff; sigma=0.45 keeps burst tight
            radial = np.exp(-dist2 / (2 * 0.45 ** 2)) * intensity  # (h, w)

            burst_light = radial[:, :, np.newaxis] * c[np.newaxis, np.newaxis, :]  # (h, w, 3)

            region = strip[:, x0:x1, :]
            strip[:, x0:x1, :] = np.minimum(region + burst_light, 255.0)

        strip = np.clip(strip, 0, 255).astype(np.uint8)
        arr[strip_top:strip_bottom] = strip
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

        # Draw faint horizontal grid lines at 25 %, 50 %, 75 % height marks
        for frac in (0.25, 0.50, 0.75):
            grid_row = strip_bottom - int(h * frac)
            grid_row = max(0, min(arr.shape[0] - 1, grid_row))
            arr[grid_row, :] = np.clip(
                arr[grid_row, :].astype(np.int16) + 20, 0, 255
            ).astype(np.uint8)

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
