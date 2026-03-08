from dataclasses import dataclass


@dataclass
class KeyInfo:
    midi: int
    x: float       # left edge x position
    width: float   # key width in pixels
    is_black: bool


# Pattern indexed from C (MIDI % 12): True = white, False = black
# C  C# D  D# E  F  F# G  G# A  A# B
OCTAVE_PATTERN = [True, False, True, False, True, True, False, True, False, True, False, True]


def build_key_map(total_width: int, margin: int = 20) -> dict[int, KeyInfo]:
    """Build pixel positions for all 88 piano keys (MIDI 21-108).

    MIDI 21 = A0, MIDI 108 = C8.
    White keys are distributed evenly across total_width - 2*margin.
    Black keys are 60% the width of white keys, offset ~65% across the preceding
    white key within the same octave group.
    """
    # MIDI % 12 gives the C-based octave position (C=0 .. B=11)
    def is_white(midi: int) -> bool:
        return OCTAVE_PATTERN[midi % 12]

    white_count = sum(1 for midi in range(21, 109) if is_white(midi))
    # Should be 52 for a standard 88-key piano

    usable_width = total_width - 2 * margin
    white_key_width = usable_width / white_count
    black_key_width = white_key_width * 0.60

    key_map: dict[int, KeyInfo] = {}
    white_index = 0  # cumulative count of white keys placed so far

    for midi in range(21, 109):
        if is_white(midi):
            x = margin + white_index * white_key_width
            key_map[midi] = KeyInfo(
                midi=midi,
                x=x,
                width=white_key_width,
                is_black=False,
            )
            white_index += 1
        else:
            # Black key sits between the white key to its left (white_index-1)
            # and the white key to its right (white_index).
            # Center it at 65% across the left white key.
            prev_white_x = margin + (white_index - 1) * white_key_width
            x = prev_white_x + white_key_width * 0.65 - black_key_width / 2
            key_map[midi] = KeyInfo(
                midi=midi,
                x=x,
                width=black_key_width,
                is_black=True,
            )

    return key_map
