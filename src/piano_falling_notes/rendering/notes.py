from PIL import Image, ImageDraw

from .layout import Layout
from .colors import ColorScheme

CORNER_RADIUS = 4
NOTE_HORIZONTAL_GAP = 1  # px gap on each side of a note bar
NOTE_VERTICAL_GAP = 0    # handled by note_duration_ratio instead

GUIDE_LINE_COLOR = (30, 30, 35)


class FallingNotesRenderer:
    def __init__(
        self,
        layout: Layout,
        color_scheme: ColorScheme,
        key_map: dict,
        note_duration_ratio: float = 0.95,
        guide_lines: bool = True,
    ):
        self.layout = layout
        self.colors = color_scheme
        self.key_map = key_map
        self.note_duration_ratio = note_duration_ratio
        self.guide_lines = guide_lines

    def render_guide_lines(self, img: Image.Image) -> None:
        """Draw faint vertical lines at octave boundaries (C notes only)."""
        draw = ImageDraw.Draw(img)
        keyboard_top = self.layout.keyboard_top
        # Only draw lines at C notes (midi % 12 == 0) — octave boundaries
        for midi, key in self.key_map.items():
            if midi % 12 == 0:  # C notes: C1=24, C2=36, C3=48, C4=60, ...
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
        if self.guide_lines:
            self.render_guide_lines(img)

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

            draw.rounded_rectangle(rect, radius=CORNER_RADIUS, fill=color_rgb)

        return img
