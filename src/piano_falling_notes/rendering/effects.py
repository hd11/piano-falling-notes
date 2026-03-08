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
