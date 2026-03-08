from dataclasses import dataclass


@dataclass
class Layout:
    width: int = 1920
    height: int = 1080
    fps: int = 60
    keyboard_height_ratio: float = 0.15
    lookahead_seconds: float = 3.0
    piano_min_midi: int = 21   # A0
    piano_max_midi: int = 108  # C8

    @property
    def keyboard_top(self) -> int:
        return int(self.height * (1.0 - self.keyboard_height_ratio))

    @property
    def keyboard_height(self) -> int:
        return self.height - self.keyboard_top

    @property
    def note_area_height(self) -> int:
        return self.keyboard_top

    def time_to_y(self, note_time: float, current_time: float) -> float:
        """Convert time to y pixel. current_time maps to keyboard_top, current_time+lookahead maps to y=0."""
        time_offset = note_time - current_time
        ratio = time_offset / self.lookahead_seconds
        return self.keyboard_top * (1.0 - ratio)
