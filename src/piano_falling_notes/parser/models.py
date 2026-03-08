from dataclasses import dataclass


@dataclass(frozen=True)
class NoteEvent:
    """Raw note extracted from MusicXML."""
    midi_number: int        # 21=A0 ~ 108=C8
    start_ticks: int        # start position in ticks
    duration_ticks: int     # duration in ticks
    velocity: float         # 0.0~1.0
    part_index: int         # part number (0-based)
    tie_continue: bool      # tied to next note
    measure_number: int     # measure number (debug)
