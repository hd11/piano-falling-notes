from dataclasses import dataclass, field

from ..parser.models import NoteEvent
from .models import RenderNote


@dataclass
class Timeline:
    notes: list[RenderNote]
    total_duration: float
    tempo_bpm: float
    title: str


def _ticks_to_seconds(ticks: int, divisions: int, tempo_bpm: float) -> float:
    quarter_notes = ticks / divisions
    return quarter_notes * (60.0 / tempo_bpm)


def build_timeline(events: list[NoteEvent], metadata: dict) -> Timeline:
    divisions: int = metadata["divisions"]
    tempo_bpm: float = float(metadata["tempo_bpm"])
    title: str = metadata.get("title", "")

    # Merge tied notes: consecutive notes with the same midi_number and part
    # where the earlier note has tie_continue=True get their durations combined.
    # We process in start_ticks order (events should already be sorted).
    sorted_events = sorted(events, key=lambda n: (n.part_index, n.midi_number, n.start_ticks))

    merged: list[NoteEvent] = []
    for ev in sorted_events:
        if (
            merged
            and merged[-1].tie_continue
            and merged[-1].midi_number == ev.midi_number
            and merged[-1].part_index == ev.part_index
        ):
            # extend the previous note's duration
            prev = merged[-1]
            merged[-1] = NoteEvent(
                midi_number=prev.midi_number,
                start_ticks=prev.start_ticks,
                duration_ticks=prev.duration_ticks + ev.duration_ticks,
                velocity=prev.velocity,
                part_index=prev.part_index,
                # keep tie_continue from the new note (chain may continue)
                tie_continue=ev.tie_continue,
                measure_number=prev.measure_number,
            )
        else:
            merged.append(ev)

    # Convert to RenderNote
    render_notes: list[RenderNote] = []
    for ev in merged:
        start_s = _ticks_to_seconds(ev.start_ticks, divisions, tempo_bpm)
        dur_s = _ticks_to_seconds(ev.duration_ticks, divisions, tempo_bpm)
        render_notes.append(RenderNote(
            midi_number=ev.midi_number,
            start_seconds=start_s,
            duration_seconds=dur_s,
            velocity=ev.velocity,
            part_index=ev.part_index,
        ))

    render_notes.sort(key=lambda n: n.start_seconds)

    total_duration = max(
        (n.start_seconds + n.duration_seconds for n in render_notes),
        default=0.0,
    )

    return Timeline(
        notes=render_notes,
        total_duration=total_duration,
        tempo_bpm=tempo_bpm,
        title=title,
    )
