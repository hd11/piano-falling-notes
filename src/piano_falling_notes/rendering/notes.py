import numpy as np
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
        velocity_effect: bool = False,
    ):
        self.layout = layout
        self.colors = color_scheme
        self.key_map = key_map
        self.note_duration_ratio = note_duration_ratio
        self.guide_lines = guide_lines
        self.glitter = glitter
        self.velocity_effect = velocity_effect
        self._note_color_cache = {}  # {(midi, start_seconds): color_rgb} — fixed on first render

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

            cache_key = (note.midi_number, note.start_seconds)
            if cache_key not in self._note_color_cache:
                color_rgba = self.colors.note_color(note.midi_number, note.velocity, note.part_index)
                self._note_color_cache[cache_key] = color_rgba[:3]
            color_rgb = self._note_color_cache[cache_key]

            if self.velocity_effect:
                brightness = 0.4 + 0.6 * note.velocity
                color_rgb = tuple(int(c * brightness) for c in color_rgb)

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
                x0i, y0i, x1i, y1i = rect
                # Clamp region to actual image bounds
                gx0 = max(0, x0i)
                gy0 = max(0, y0i)
                gx1 = min(img.width, x1i)
                gy1 = min(img.height, y1i)
                if gx1 <= gx0 or gy1 <= gy0:
                    continue

                # Extract region as numpy array (H, W, channels)
                region = np.array(img.crop((gx0, gy0, gx1, gy1)), dtype=np.float32)

                # Build mask: pixels that match color_rgb (rounded rect area vs background)
                cr, cg, cb = color_rgb
                mask = (
                    (region[:, :, 0] == cr) &
                    (region[:, :, 1] == cg) &
                    (region[:, :, 2] == cb)
                )  # shape (H, W), bool

                # Build vertical gradient: t=0 at top, t=1 at bottom
                h_region = gy1 - gy0
                row_offsets = np.arange(gy0, gy1, dtype=np.float32) - y0i
                t = row_offsets / max(note_h - 1, 1)
                # Full-height gradient: white at top (t=0) fading to pure color at bottom (t=1)
                base_intensity = 0.7
                if self.velocity_effect:
                    # Scale gradient intensity by velocity (0-1 → 0.3-1.0 range)
                    vel = note.velocity
                    vel_scale = 0.3 + vel * 0.7
                    base_intensity *= vel_scale
                white_mix = (base_intensity * (1.0 - t)).reshape(h_region, 1)  # (H, 1)

                # Gradient target colors broadcast over width
                base_r = cr * (1.0 - white_mix) + 255.0 * white_mix  # (H, 1)
                base_g = cg * (1.0 - white_mix) + 255.0 * white_mix
                base_b = cb * (1.0 - white_mix) + 255.0 * white_mix

                # Stack to (H, 1, 3) for broadcasting against (H, W, 3)
                gradient = np.stack([base_r, base_g, base_b], axis=2)  # (H, 1, 3)

                if self.glitter:
                    seed = note.midi_number * 137 + int(note.start_seconds * 100)
                    w_region = gx1 - gx0
                    # Vectorized hash: shape (H, W) using uint32 arithmetic
                    gx_arr = np.arange(gx0, gx1, dtype=np.uint32)                      # (W,)
                    gy_arr = np.arange(gy0, gy1, dtype=np.uint32) - np.uint32(y0i)    # (H,) rel_y
                    seed_u32 = np.uint32(seed)
                    # Broadcast: (H, 1) ^ (1, W) ^ scalar
                    hval = (
                        (gx_arr[np.newaxis, :] * np.uint32(2654435761)) ^
                        (gy_arr[:, np.newaxis] * np.uint32(2246822519)) ^
                        (seed_u32 * np.uint32(3266489917))
                    )  # (H, W), uint32
                    sv = ((hval >> np.uint32(8)) & np.uint32(0xFF)).astype(np.float32)  # (H, W)
                    phase_raw = (hval & np.uint32(0xFF)).astype(np.float32) / 255.0 * 6.283
                    twinkle = 0.5 + 0.5 * np.sin(current_time * 6.0 + phase_raw)  # (H, W)

                    sparkle = np.zeros((h_region, w_region), dtype=np.float32)
                    hi_mask = sv > 235
                    lo_mask = (sv > 200) & ~hi_mask
                    sparkle[hi_mask] = (sv[hi_mask] - 235.0) / 20.0 * 120.0 * twinkle[hi_mask]
                    sparkle[lo_mask] = (sv[lo_mask] - 200.0) / 35.0 * 35.0 * twinkle[lo_mask]
                    # Add sparkle only where mask is true; shape (H, W, 1) for broadcast
                    sparkle_3d = (sparkle * mask)[:, :, np.newaxis]
                    gradient = gradient + sparkle_3d

                # Apply gradient to masked pixels; non-masked pixels keep original values
                mask_3d = mask[:, :, np.newaxis]  # (H, W, 1)
                result = np.where(mask_3d, np.clip(gradient, 0, 255), region)
                result_uint8 = result.astype(np.uint8)

                # Write back to image
                patch = Image.fromarray(result_uint8, mode=img.mode)
                img.paste(patch, (gx0, gy0))

        # Draw guide lines AFTER notes so they're always visible on top
        if self.guide_lines:
            self.render_guide_lines(img)

        return img
