from PIL import Image, ImageDraw

from .layout import Layout
from .colors import ColorScheme
from ..utils.piano_keys import build_key_map, KeyInfo

# Colors for inactive keys
WHITE_KEY_COLOR = (240, 240, 240)
BLACK_KEY_COLOR = (30, 30, 30)
KEY_BORDER_COLOR = (80, 80, 80)


class KeyboardRenderer:
    def __init__(self, layout: Layout, color_scheme: ColorScheme):
        self.layout = layout
        self.colors = color_scheme
        self.keys = build_key_map(layout.width)
        self._base_image = self._render_base()

    def _render_base(self) -> Image.Image:
        """Render static keyboard (no active keys)."""
        kh = self.layout.keyboard_height
        w = self.layout.width

        img = Image.new("RGB", (w, kh), color=(20, 20, 20))
        draw = ImageDraw.Draw(img)

        white_bottom = kh - 1
        black_bottom = int(kh * 0.60)

        # Draw all white keys first
        for key in self.keys.values():
            if key.is_black:
                continue
            x0 = int(key.x)
            x1 = int(key.x + key.width) - 1
            draw.rectangle([x0, 0, x1, white_bottom], fill=WHITE_KEY_COLOR, outline=KEY_BORDER_COLOR)

        # Draw black keys on top
        for key in self.keys.values():
            if not key.is_black:
                continue
            x0 = int(key.x)
            x1 = int(key.x + key.width)
            draw.rectangle([x0, 0, x1, black_bottom], fill=BLACK_KEY_COLOR)

        return img

    def render(self, active_notes: dict[int, float]) -> Image.Image:
        """Render keyboard with active notes highlighted.

        active_notes: {midi_number: velocity}
        Returns an RGB image of keyboard_height pixels tall.
        """
        img = self._base_image.copy()
        draw = ImageDraw.Draw(img)

        kh = self.layout.keyboard_height
        white_bottom = kh - 1
        black_bottom = int(kh * 0.60)

        # Highlight active white keys first
        for midi, velocity in active_notes.items():
            key = self.keys.get(midi)
            if key is None or key.is_black:
                continue
            color_rgb = self.colors.note_color_rgb(midi, velocity)
            x0 = int(key.x)
            x1 = int(key.x + key.width) - 1
            draw.rectangle([x0, 0, x1, white_bottom], fill=color_rgb, outline=KEY_BORDER_COLOR)

        # Re-draw all black keys (inactive) so they stay on top of highlighted white keys
        for key in self.keys.values():
            if not key.is_black:
                continue
            midi = key.midi
            if midi in active_notes:
                continue
            x0 = int(key.x)
            x1 = int(key.x + key.width)
            draw.rectangle([x0, 0, x1, black_bottom], fill=BLACK_KEY_COLOR)

        # Highlight active black keys on top of everything
        for midi, velocity in active_notes.items():
            key = self.keys.get(midi)
            if key is None or not key.is_black:
                continue
            color_rgb = self.colors.note_color_rgb(midi, velocity)
            # Brighten slightly for black keys so they read clearly
            bright = tuple(min(255, int(c * 1.25)) for c in color_rgb)
            x0 = int(key.x)
            x1 = int(key.x + key.width)
            draw.rectangle([x0, 0, x1, black_bottom], fill=bright)

        return img
