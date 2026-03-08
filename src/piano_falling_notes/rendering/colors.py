import colorsys


# PianiCast-style palette: 12 semitone colors (vibrant, distinct)
CHROMATIC_COLORS = [
    (255, 50, 50),    # C  - red
    (255, 120, 30),   # C# - orange-red
    (255, 190, 0),    # D  - orange-yellow
    (230, 255, 0),    # D# - yellow-green
    (80, 255, 80),    # E  - green
    (0, 230, 160),    # F  - teal
    (0, 200, 255),    # F# - cyan
    (30, 120, 255),   # G  - blue
    (100, 60, 255),   # G# - indigo
    (180, 40, 255),   # A  - purple
    (255, 50, 200),   # A# - magenta
    (255, 60, 120),   # B  - pink
]


class ColorScheme:
    def __init__(self, mode: str = "pitch_range"):
        self.mode = mode

    def note_color(self, midi_number: int, velocity: float = 1.0, part_index: int = 0) -> tuple[int, int, int, int]:
        """Return RGBA color for a note."""
        if self.mode == "pitch_range":
            return self._pitch_range_color(midi_number, velocity)
        elif self.mode == "rainbow_octave":
            return self._rainbow_color(midi_number, velocity)
        return self._pitch_range_color(midi_number, velocity)

    def _pitch_range_color(self, midi_number: int, velocity: float) -> tuple[int, int, int, int]:
        """HSV gradient: low notes=warm (red/orange), high notes=cool (blue/purple)."""
        ratio = (midi_number - 21) / 87.0
        hue = ratio * 0.75
        saturation = 0.8 + velocity * 0.2
        value = 0.85 + velocity * 0.15
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        return (int(r * 255), int(g * 255), int(b * 255), 255)

    def _rainbow_color(self, midi_number: int, velocity: float) -> tuple[int, int, int, int]:
        """Chromatic colors: each semitone gets a distinct vivid color."""
        note_in_octave = midi_number % 12
        base = CHROMATIC_COLORS[note_in_octave]
        # Slightly adjust brightness by octave (higher octave = brighter)
        octave = (midi_number - 21) // 12
        brightness = 0.75 + octave * 0.07  # 0.75 ~ 1.0+
        brightness = min(1.0, brightness) * (0.8 + velocity * 0.2)
        r = min(255, int(base[0] * brightness))
        g = min(255, int(base[1] * brightness))
        b = min(255, int(base[2] * brightness))
        return (r, g, b, 255)

    def note_color_rgb(self, midi_number: int, velocity: float = 1.0) -> tuple[int, int, int]:
        """Return RGB only (no alpha)."""
        rgba = self.note_color(midi_number, velocity)
        return rgba[:3]
