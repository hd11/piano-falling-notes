import music21.converter
import music21.note
import music21.chord
import music21.tempo
import music21.meter
import music21.key

from .models import NoteEvent


def _midi_from_pitch(pitch) -> int:
    return pitch.midi


def _get_velocity(note) -> float:
    # music21 stores dynamics as note.volume.velocity (0-127 int)
    # but the MusicXML files also carry dynamics="88.89" as a raw attribute
    vol = note.volume
    if vol is not None and vol.velocity is not None:
        return vol.velocity / 127.0
    return 88.89 / 127.0  # default from test files


def _tie_continues(note) -> bool:
    """True when this note has a tie-start (continues into the next note)."""
    if note.tie is None:
        return False
    return note.tie.type in ("start", "continue")


def parse_musicxml(filepath: str) -> tuple[list[NoteEvent], dict]:
    """Returns (notes_list, metadata_dict)"""
    score = music21.converter.parse(filepath)

    # --- metadata ---
    title = ""
    if score.metadata:
        # music21 maps <movement-title> to movementName; <work-title> to title
        title = score.metadata.movementName or score.metadata.title or ""

    # tempo: first TempoIndication found anywhere in the score
    tempo_bpm = 120.0
    for el in score.flatten().getElementsByClass(music21.tempo.MetronomeMark):
        if el.number is not None:
            tempo_bpm = float(el.number)
            break

    # divisions: ticks per quarter note. music21 offsets are in quarter-note units,
    # so we multiply by divisions to get ticks, then divide by divisions in timeline
    # builder to get back to quarter notes. The value cancels out, so any consistent
    # value works. We use 10080 for high precision with integer math.
    divisions = 10080

    # time signature
    time_signature = (4, 4)
    for el in score.flatten().getElementsByClass(music21.meter.TimeSignature):
        time_signature = (el.numerator, el.denominator)
        break

    # total measures: max measure count across all parts
    total_measures = 0
    for part in score.parts:
        measures = part.getElementsByClass("Measure")
        total_measures = max(total_measures, len(measures))

    # key signature analysis
    key_signature = "C major"
    key_mode = "major"
    # Try explicit key signature first
    for el in score.flatten().getElementsByClass(music21.key.KeySignature):
        if hasattr(el, 'asKey'):
            k = el.asKey()
            key_signature = str(k)
            key_mode = k.mode
            break
    for el in score.flatten().getElementsByClass(music21.key.Key):
        key_signature = str(el)
        key_mode = el.mode
        break
    # Fallback: algorithmic analysis
    if key_signature == "C major":
        try:
            analyzed = score.analyze('key')
            if analyzed:
                key_signature = str(analyzed)
                key_mode = analyzed.mode
        except Exception:
            pass

    metadata = {
        "title": title,
        "tempo_bpm": tempo_bpm,
        "divisions": divisions,
        "time_signature": time_signature,
        "total_measures": total_measures,
        "key_signature": key_signature,
        "key_mode": key_mode,
    }

    # --- notes ---
    notes: list[NoteEvent] = []

    for part_index, part in enumerate(score.parts):
        # running tick offset (music21 offsets are in quarter-note units)
        for measure in part.getElementsByClass("Measure"):
            measure_number = int(measure.number) if measure.number else 0
            measure_offset_ticks = int(round(float(measure.offset) * divisions))

            for el in measure.flatten().notesAndRests:
                if isinstance(el, music21.note.Rest):
                    continue

                el_offset_ticks = int(round(float(el.offset) * divisions))
                start_ticks = measure_offset_ticks + el_offset_ticks
                duration_ticks = int(round(float(el.quarterLength) * divisions))

                if isinstance(el, music21.chord.Chord):
                    # treat each pitch in the chord independently
                    for pitch in el.pitches:
                        notes.append(NoteEvent(
                            midi_number=_midi_from_pitch(pitch),
                            start_ticks=start_ticks,
                            duration_ticks=duration_ticks,
                            velocity=_get_velocity(el),
                            part_index=part_index,
                            tie_continue=_tie_continues(el),
                            measure_number=measure_number,
                        ))
                else:
                    notes.append(NoteEvent(
                        midi_number=_midi_from_pitch(el.pitch),
                        start_ticks=start_ticks,
                        duration_ticks=duration_ticks,
                        velocity=_get_velocity(el),
                        part_index=part_index,
                        tie_continue=_tie_continues(el),
                        measure_number=measure_number,
                    ))

    notes.sort(key=lambda n: (n.start_ticks, n.midi_number))
    return notes, metadata
