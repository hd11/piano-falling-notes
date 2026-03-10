# AGENTS.md - timeline

Parent: ../AGENTS.md

Timeline package — temporal organization of notes for rendering.

## Files

### models.py

Timeline data structures.

**Key dataclass:**
- `Timeline` (mutable)
  - `notes: list[RenderNote]` — Sorted list of notes (by start_seconds)
  - `total_duration: float` — Longest note end time (seconds)
  - `tempo_bpm: float` — Average tempo (beats per minute)
  - `title: str` — Score title

**Key dataclass:**
- `RenderNote` (frozen) — Note ready for rendering with time in seconds
  - `midi_number: int` — MIDI pitch
  - `start_seconds: float` — Start time in seconds
  - `duration_seconds: float` — Duration in seconds
  - `velocity: float` — Normalized velocity (0.0–1.0)
  - `part_index: int` — Part number (0-based)

### builder.py

TimelineBuilder: converts parsed notes into frame-indexed render data.

**Key function:**
- `build_timeline(events: list[NoteEvent], metadata: dict) -> Timeline` — Convert parsed NoteEvent list to renderer-ready Timeline
  1. Extract metadata: divisions, tempo_bpm, tempo_map, title
  2. Sort events by (part_index, midi_number, start_ticks)
  3. Merge tied notes: consecutive notes with same midi_number, part_index, and tie_continue=True get their durations combined
  4. Convert ticks to seconds using tempo_map
  5. Create RenderNote for each event
  6. Sort RenderNote list by start_seconds
  7. Compute total_duration
  8. Return Timeline

**Helper function:**
- `_ticks_to_seconds(ticks: int, divisions: int, tempo_map: list[tuple[int, float]]) -> float` — Convert tick position to seconds
  - tempo_map is list of (tick, bpm) sorted by tick
  - Accumulates time across tempo changes

**Tied note merging:** When a note has tie_continue=True, its duration is added to the next note with the same midi_number and part_index. This creates seamless long notes in rendering.

### time_index.py

TimeIndex: fast lookup of active notes at any given time point.

**Key class:**
- `TimeIndex(notes: list[RenderNote])` — Binary-search index for O(log N + K) queries
  - `__init__()` — Sort notes by start_seconds; cache starts and ends
  - `query(view_top_time: float, view_bottom_time: float) -> list[RenderNote]` — Return notes visible in time range

**Query logic:**
- A note is visible when: `note.start_seconds < view_bottom_time AND note.end_seconds > view_top_time`
- Uses bisect.bisect_left() to find upper bound on start_seconds
- Linearly scans to check end_seconds
- Returns all visible notes in O(log N + K) where K is result count

**Use case:** Per-frame rendering queries "what notes are visible at this frame time?"

## Integration Notes

- Timeline is immutable after creation (frozen RenderNote dataclass)
- All times are absolute seconds from score start
- RenderNote velocity is normalized (0.0–1.0) for rendering color/opacity effects
- TimeIndex is created once per render session for fast per-frame queries
- Tempo changes are absorbed in the ticks-to-seconds conversion; RenderNote times are absolute
