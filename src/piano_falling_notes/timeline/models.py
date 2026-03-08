from dataclasses import dataclass


@dataclass(frozen=True)
class RenderNote:
    """Note ready for rendering with time in seconds."""
    midi_number: int
    start_seconds: float
    duration_seconds: float
    velocity: float
    part_index: int
