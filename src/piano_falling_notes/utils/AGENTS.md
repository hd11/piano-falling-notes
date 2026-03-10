# AGENTS.md - utils

Parent: ../AGENTS.md

Utilities package — shared helper functions and constants.

## Files

### piano_keys.py

Piano key definitions: 88-key layout, MIDI number mappings, white/black key classification, note name lookups.

**Key constants:**
- `OCTAVE_PATTERN` — List[bool] indexed by MIDI % 12 (C-based octave position)
  - True = white key, False = black key
  - Pattern: [C=T, C#=F, D=T, D#=F, E=T, F=T, F#=F, G=T, G#=F, A=T, A#=F, B=T]

**Key dataclass:**
- `KeyInfo` — Pixel position metadata for one key
  - `midi: int` — MIDI number
  - `x: float` — Left edge x position (pixels)
  - `width: float` — Key width (pixels)
  - `is_black: bool` — True for black keys

**Key function:**
- `build_key_map(total_width: int, margin: int=20) -> dict[int, KeyInfo]` — Build pixel positions for all 88 piano keys (MIDI 21–108)
  1. Count white keys in range (should be 52)
  2. Calculate white_key_width = (total_width - 2*margin) / white_count
  3. Calculate black_key_width = white_key_width * 0.60
  4. Iterate MIDI 21–108:
     - White keys: place at cumulative x position
     - Black keys: center at boundary between adjacent white keys, offset -30% of black_key_width left
  5. Return dict mapping MIDI number → KeyInfo

**MIDI range:** 21 (A0) to 108 (C8) represents all 88 piano keys.

**Layout logic:**
- White keys are distributed evenly across usable width
- Black keys are 60% white key width
- Black key placement: centered at boundary between white keys, offset to appear "between" them visually
- Margin prevents keys from reaching screen edges

## Integration Notes

- Used by rendering.keyboard.KeyboardRenderer to convert note MIDI → pixel position
- Used by rendering.notes.FallingNotesRenderer to center note bars above keys
- OCTAVE_PATTERN is recomputed from MIDI % 12 for any note; no lookup table needed
- KeyInfo positions are computed once at render initialization and cached in Layout
