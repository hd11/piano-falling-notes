# AGENTS.md - parser

Parent: ../AGENTS.md

Parser package — score file parsing.

## Files

### models.py

Data models for parsed score content.

**Key dataclass:**
- `NoteEvent` (frozen) — Raw note extracted from MusicXML
  - `midi_number: int` — MIDI pitch (21=A0 to 108=C8, 88-key piano range)
  - `start_ticks: int` — Start position in score divisions (ticks)
  - `duration_ticks: int` — Duration in ticks
  - `velocity: float` — Normalized velocity (0.0–1.0)
  - `part_index: int` — Part number (0-based, for multi-staff scores)
  - `tie_continue: bool` — True if tied to next note (for merging tied notes)
  - `measure_number: int` — Measure number (debug metadata)

**Frozen constraint:** NoteEvent instances are immutable; never modify after creation.

### musicxml_parser.py

Parses MusicXML (.mxl/.xml) and MIDI (.mid/.midi) files using music21.

**Key functions:**
- `parse_musicxml(file_path: str) -> tuple[list[NoteEvent], dict]` — Parse score file (MusicXML or MIDI)
  - Returns notes list and metadata dict
  - Metadata keys: `divisions` (ticks per quarter), `tempo_bpm` (float), `tempo_map` (list of (tick, bpm) tuples), `title` (str), `key_signature` (str), `time_signature` (str), `parts_count` (int)

- `_extract_pedal_events(score, divisions, tempo_map) -> list[dict]` — Extract sustain pedal events
  - Returns list of `{start_seconds, end_seconds}` dicts
  - Method 1: Look for PedalMark expressions in MusicXML
  - Method 2: Fall back to MIDI CC64 controller events
  - Converts tick positions to seconds using tempo_map

**Helper functions:**
- `_midi_from_pitch(pitch)` — Extract MIDI number from music21 Pitch
- `_get_velocity(note) -> float` — Extract velocity (0.0–1.0) from note.volume or default to ~0.7
- `_tie_continues(note) -> bool` — Check if note has tie-start or tie-continue

**Parsing logic:**
1. Open file with music21.converter.parse()
2. Extract divisions (ticks per quarter note) from score metadata
3. Iterate through parts and measures, collecting notes and dynamics
4. Build tempo_map from tempo changes
5. Extract key signature, time signature, part count
6. Extract pedal events (optional)
7. Sort notes by (part, midi, start_ticks)
8. Return NoteEvent list + metadata

**Tied note handling:** Notes with `tie_continue=True` indicate the note extends into the next note; they are merged in timeline.builder.

**Velocity handling:** Normalized from music21 volume.velocity (0–127 int) or MusicXML dynamics attribute.

## Integration Notes

- All notes are returned in a single flat list (not grouped by part)
- Metadata tempo_map enables accurate timing across tempo changes
- Pedal events are optional for visual pedal-down indicator rendering
- Parser is agnostic to audio synthesis; just extracts structural data
