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

NEON_PALETTE = [
    (255, 0, 60),
    (255, 80, 0),
    (255, 255, 0),
    (0, 255, 80),
    (0, 255, 200),
    (0, 255, 255),
    (0, 160, 255),
    (0, 80, 255),
    (130, 0, 255),
    (255, 0, 255),
    (255, 0, 160),
    (255, 60, 100),
]

# Mode aliases: maps incoming mode name to canonical mode name
_MODE_ALIASES = {"rainbow_octave": "rainbow"}

# Colors for the "part" mode (one color per part index)
_PART_COLORS = [
    (0, 200, 255),    # Part 0 - cyan
    (255, 100, 60),   # Part 1 - warm orange
    (100, 255, 80),   # Part 2 - green (fallback)
    (255, 60, 200),   # Part 3 - magenta (fallback)
]


class ColorScheme:
    def __init__(
        self,
        mode: str = "pitch_range",
        palette: tuple | None = None,
        single_color: tuple = (0, 210, 210),
        white_key_note_color: tuple = (0, 255, 128),
        black_key_note_color: tuple = (0, 128, 255),
    ):
        canonical = _MODE_ALIASES.get(mode, mode)
        self.mode = canonical
        self.palette = palette  # custom 12-color palette overrides CHROMATIC_COLORS
        self.single_color = single_color
        self.white_key_note_color = white_key_note_color
        self.black_key_note_color = black_key_note_color

    def note_color(self, midi_number: int, velocity: float = 1.0, part_index: int = 0) -> tuple[int, int, int, int]:
        """Return RGBA color for a note."""
        mode = self.mode
        if mode == "single":
            return self._single_color(velocity)
        elif mode in ("rainbow", "rainbow_octave"):
            return self._rainbow_color(midi_number, velocity)
        elif mode == "neon":
            return self._neon_color(midi_number, velocity)
        elif mode == "part":
            return self._part_color(part_index, velocity)
        elif mode == "pitch_range":
            return self._pitch_range_color(midi_number, velocity)
        elif mode == "key_type":
            return self._key_type_color(midi_number, velocity)
        # Default fallback
        return self._single_color(velocity)

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
        colors = self.palette if self.palette else CHROMATIC_COLORS
        base = colors[note_in_octave]
        # Slightly adjust brightness by octave (higher octave = brighter)
        octave = (midi_number - 21) // 12
        brightness = 0.75 + octave * 0.07  # 0.75 ~ 1.0+
        brightness = min(1.0, brightness) * (0.8 + velocity * 0.2)
        r = min(255, int(base[0] * brightness))
        g = min(255, int(base[1] * brightness))
        b = min(255, int(base[2] * brightness))
        return (r, g, b, 255)

    def _single_color(self, velocity: float) -> tuple[int, int, int, int]:
        """Returns self.single_color with velocity-based brightness (0.7 + velocity * 0.3)."""
        brightness = 0.7 + velocity * 0.3
        r = min(255, int(self.single_color[0] * brightness))
        g = min(255, int(self.single_color[1] * brightness))
        b = min(255, int(self.single_color[2] * brightness))
        return (r, g, b, 255)

    def _neon_color(self, midi_number: int, velocity: float) -> tuple[int, int, int, int]:
        """Same as _rainbow_color but forces the NEON_PALETTE."""
        note_in_octave = midi_number % 12
        base = NEON_PALETTE[note_in_octave]
        octave = (midi_number - 21) // 12
        brightness = 0.75 + octave * 0.07
        brightness = min(1.0, brightness) * (0.8 + velocity * 0.2)
        r = min(255, int(base[0] * brightness))
        g = min(255, int(base[1] * brightness))
        b = min(255, int(base[2] * brightness))
        return (r, g, b, 255)

    def _part_color(self, part_index: int, velocity: float) -> tuple[int, int, int, int]:
        """Distinct color per part, brightness modulated by velocity."""
        base = _PART_COLORS[part_index % len(_PART_COLORS)]
        brightness = 0.7 + velocity * 0.3
        r = min(255, int(base[0] * brightness))
        g = min(255, int(base[1] * brightness))
        b = min(255, int(base[2] * brightness))
        return (r, g, b, 255)

    def _key_type_color(self, midi_number: int, velocity: float) -> tuple[int, int, int, int]:
        """Green for white keys, blue for black keys, brightness modulated by velocity."""
        is_black = (midi_number % 12) in {1, 3, 6, 8, 10}
        base = self.black_key_note_color if is_black else self.white_key_note_color
        brightness = 0.7 + velocity * 0.3
        r = min(255, int(base[0] * brightness))
        g = min(255, int(base[1] * brightness))
        b = min(255, int(base[2] * brightness))
        return (r, g, b, 255)

    def note_color_rgb(self, midi_number: int, velocity: float = 1.0) -> tuple[int, int, int]:
        """Return RGB only (no alpha)."""
        rgba = self.note_color(midi_number, velocity)
        return rgba[:3]
