from PIL import Image, ImageDraw

from .layout import Layout
from .colors import ColorScheme

CORNER_RADIUS = 4
NOTE_HORIZONTAL_GAP = 1  # px gap on each side of a note bar
NOTE_VERTICAL_GAP = 0    # handled by note_duration_ratio instead

GUIDE_LINE_COLOR = (60, 60, 75)


class FallingNotesRenderer:
    def __init__(
        self,
        layout: Layout,
        color_scheme: ColorScheme,
        key_map: dict,
        note_duration_ratio: float = 0.95,
        guide_lines: bool = True,
        glitter: bool = False,
    ):
        self.layout = layout
        self.colors = color_scheme
        self.key_map = key_map
        self.note_duration_ratio = note_duration_ratio
        self.guide_lines = guide_lines
        self.glitter = glitter

    def render_guide_lines(self, img: Image.Image) -> None:
        """Draw faint vertical lines at C and F note boundaries."""
        draw = ImageDraw.Draw(img)
        keyboard_top = self.layout.keyboard_top
        for midi, key in self.key_map.items():
            if midi % 12 == 0 or midi % 12 == 5:  # C (도) and F (파)
                x = int(key.x)
                draw.line([(x, 0), (x, keyboard_top)], fill=GUIDE_LINE_COLOR, width=1)

    def render(self, img: Image.Image, visible_notes: list, current_time: float) -> Image.Image:
        """Draw falling note bars onto img and return it.

        For each RenderNote in visible_notes:
          - x / width from key_map (matching the piano key position)
          - y_bottom = time_to_y(note.start_seconds, current_time)
          - y_top    = time_to_y(visual_end, current_time)  where visual_end uses note_duration_ratio
          - Clipped to [0, keyboard_top]
          - Drawn as a rounded rectangle in the note's color
        """
        draw = ImageDraw.Draw(img)
        keyboard_top = self.layout.keyboard_top

        for note in visible_notes:
            key = self.key_map.get(note.midi_number)
            if key is None:
                continue

            y_bottom = self.layout.time_to_y(note.start_seconds, current_time)
            visual_end = note.start_seconds + note.duration_seconds * self.note_duration_ratio
            y_top = self.layout.time_to_y(visual_end, current_time)

            # Notes fully below the keyboard or fully above the frame are invisible
            if y_top >= keyboard_top or y_bottom <= 0:
                continue

            # Clip to note area (0 .. keyboard_top)
            y_top_clipped = max(0.0, y_top)
            y_bottom_clipped = min(float(keyboard_top), y_bottom)

            if y_bottom_clipped <= y_top_clipped:
                continue

            x0 = key.x + NOTE_HORIZONTAL_GAP
            x1 = key.x + key.width - NOTE_HORIZONTAL_GAP

            if x1 <= x0:
                continue

            color_rgba = self.colors.note_color(note.midi_number, note.velocity, note.part_index)
            color_rgb = color_rgba[:3]

            # Pillow's rounded_rectangle requires integer coords
            rect = [
                int(x0),
                int(y_top_clipped),
                int(x1),
                int(y_bottom_clipped),
            ]

            # Ensure minimum 1px height so very short notes are still visible
            if rect[3] <= rect[1]:
                rect[3] = rect[1] + 1

            # White-top gradient (+ optional twinkling glitter)
            note_h = rect[3] - rect[1]
            if note_h <= 2:
                draw.rounded_rectangle(rect, radius=CORNER_RADIUS, fill=color_rgb)
            else:
                draw.rounded_rectangle(rect, radius=CORNER_RADIUS, fill=color_rgb)
                pixels = img.load()
                x0i, y0i, x1i, y1i = rect
                if self.glitter:
                    import math
                    seed = note.midi_number * 137 + int(note.start_seconds * 100)
                for gy in range(max(0, y0i), min(img.height, y1i)):
                    t = (gy - y0i) / max(note_h - 1, 1)
                    # Full-height gradient: white at top (t=0) fading to pure color at bottom (t=1)
                    white_mix = 0.7 * (1.0 - t)
                    base_r = color_rgb[0] * (1.0 - white_mix) + 255 * white_mix
                    base_g = color_rgb[1] * (1.0 - white_mix) + 255 * white_mix
                    base_b = color_rgb[2] * (1.0 - white_mix) + 255 * white_mix
                    for gx in range(max(0, x0i), min(img.width, x1i)):
                        px = pixels[gx, gy]
                        if px[0] == color_rgb[0] and px[1] == color_rgb[1] and px[2] == color_rgb[2]:
                            sparkle = 0.0
                            if self.glitter:
                                rel_y = gy - y0i
                                h = ((gx * 2654435761) ^ (rel_y * 2246822519) ^ (seed * 3266489917)) & 0xFFFFFFFF
                                sv = (h >> 8) & 0xFF
                                if sv > 200:
                                    phase = (h & 0xFF) / 255.0 * 6.283
                                    twinkle = 0.5 + 0.5 * math.sin(current_time * 6.0 + phase)
                                    if sv > 235:
                                        sparkle = (sv - 235) / 20.0 * 120 * twinkle
                                    else:
                                        sparkle = (sv - 200) / 35.0 * 35 * twinkle
                            nr = min(255, int(base_r + sparkle))
                            ng = min(255, int(base_g + sparkle))
                            nb = min(255, int(base_b + sparkle))
                            pixels[gx, gy] = (nr, ng, nb)

        # Draw guide lines AFTER notes so they're always visible on top
        if self.guide_lines:
            self.render_guide_lines(img)

        return img
