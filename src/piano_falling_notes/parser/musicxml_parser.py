import music21.converter
import music21.note
import music21.chord
import music21.tempo
import music21.meter
import music21.key
import music21.expressions

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


def _extract_pedal_events(score, divisions: int, tempo_map: list) -> list[dict]:
    """Extract sustain pedal events from score.

    Returns list of {start_seconds, end_seconds} for each pedal down/up pair.
    Looks for PedalMark expressions (start/stop) in the MusicXML, then falls
    back to MIDI CC64 controller events.
    """

    def _ticks_to_seconds(ticks, t_map):
        """Convert tick position to seconds using tempo map."""
        seconds = 0.0
        prev_tick = 0
        prev_bpm = t_map[0][1]
        for map_tick, map_bpm in t_map:
            if map_tick >= ticks:
                break
            if map_tick > prev_tick:
                seconds += (map_tick - prev_tick) / divisions * (60.0 / prev_bpm)
            prev_tick = map_tick
            prev_bpm = map_bpm
        seconds += (ticks - prev_tick) / divisions * (60.0 / prev_bpm)
        return seconds

    pedal_events = []

    from music21.expressions import PedalMark as _PedalMark

    # Method 1: Look for PedalMark expressions (start/stop pairs)
    for part in score.parts:
        flat = part.flatten()
        pedal_marks = []
        for el in flat.getElementsByClass(_PedalMark):
            offset_ticks = int(round(float(el.offset) * divisions))
            pedal_marks.append((offset_ticks, el))

        # Pair start/stop marks
        pedal_on_tick = None
        for ticks, mark in sorted(pedal_marks, key=lambda x: x[0]):
            # PedalMark with form "start" or type containing "start"
            form_str = str(getattr(mark, 'pedalForm', '')).lower()
            is_start = 'start' in form_str or form_str == ''
            is_stop = 'stop' in form_str or 'change' in form_str

            if pedal_on_tick is None and not is_stop:
                pedal_on_tick = ticks
            elif pedal_on_tick is not None and is_stop:
                pedal_events.append({
                    'start_seconds': _ticks_to_seconds(pedal_on_tick, tempo_map),
                    'end_seconds': _ticks_to_seconds(ticks, tempo_map),
                })
                # "change" means release+repress immediately
                if 'change' in form_str:
                    pedal_on_tick = ticks
                else:
                    pedal_on_tick = None

    # Method 2: Fall back to MIDI controller 64 events (sustain pedal)
    if not pedal_events:
        try:
            import music21.midi
            import music21.midi.translate
            mf = music21.midi.translate.streamToMidiFile(score)
            for track in mf.tracks:
                pedal_on_tick = None
                running_tick = 0
                for event in track.events:
                    running_tick += event.time if hasattr(event, 'time') else 0
                    if (hasattr(event, 'type') and
                        event.type == music21.midi.ChannelVoiceMessages.CONTROLLER_CHANGE and
                        hasattr(event, 'parameter1') and event.parameter1 == 64):
                        if hasattr(event, 'parameter2'):
                            if event.parameter2 >= 64 and pedal_on_tick is None:
                                pedal_on_tick = running_tick
                            elif event.parameter2 < 64 and pedal_on_tick is not None:
                                pedal_events.append({
                                    'start_seconds': _ticks_to_seconds(pedal_on_tick, tempo_map),
                                    'end_seconds': _ticks_to_seconds(running_tick, tempo_map),
                                })
                                pedal_on_tick = None
        except Exception:
            pass

    return pedal_events


def parse_musicxml(filepath: str) -> tuple[list[NoteEvent], dict]:
    """Returns (notes_list, metadata_dict).

    Accepts MusicXML (.musicxml, .mxl, .xml) and MIDI (.mid, .midi) files.
    """
    score = music21.converter.parse(filepath)

    # --- metadata ---
    title = ""
    if score.metadata:
        # music21 maps <movement-title> to movementName; <work-title> to title
        title = score.metadata.movementName or score.metadata.title or ""

    # divisions: ticks per quarter note (fixed value, cancels out in conversion)
    divisions = 10080

    # Cache flattened score to avoid repeated traversals
    flat = score.flatten()

    # tempo map: all MetronomeMarks with their positions
    tempo_bpm = None
    tempo_map = []
    for el in flat.getElementsByClass(music21.tempo.MetronomeMark):
        if el.number is not None:
            tick_pos = int(round(float(el.offset) * divisions))
            # Convert to quarter-note BPM: dotted quarter=122 → 122*1.5=183 QN BPM
            effective_bpm = float(el.number) * float(el.referent.quarterLength)
            tempo_map.append((tick_pos, effective_bpm))
            if tempo_bpm is None:
                tempo_bpm = effective_bpm
    if tempo_bpm is None:
        tempo_bpm = 120.0
    if not tempo_map:
        tempo_map = [(0, tempo_bpm)]
    else:
        tempo_map.sort()
        if tempo_map[0][0] > 0:
            tempo_map.insert(0, (0, tempo_map[0][1]))

    # time signature
    time_signature = (4, 4)
    for el in flat.getElementsByClass(music21.meter.TimeSignature):
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
    key_found = False
    # Try explicit key signature first
    for el in flat.getElementsByClass(music21.key.KeySignature):
        if hasattr(el, 'asKey'):
            k = el.asKey()
            key_signature = str(k)
            key_mode = k.mode
            key_found = True
            break
    if not key_found:
        for el in flat.getElementsByClass(music21.key.Key):
            key_signature = str(el)
            key_mode = el.mode
            key_found = True
            break
    # Fallback: algorithmic analysis
    if not key_found:
        try:
            analyzed = score.analyze('key')
            if analyzed:
                key_signature = str(analyzed)
                key_mode = analyzed.mode
        except Exception:
            pass

    # Extract pedal events
    pedal_events = _extract_pedal_events(score, divisions, tempo_map)

    metadata = {
        "title": title,
        "tempo_bpm": tempo_bpm,
        "divisions": divisions,
        "time_signature": time_signature,
        "total_measures": total_measures,
        "key_signature": key_signature,
        "key_mode": key_mode,
        "tempo_map": tempo_map,
        "pedal_events": pedal_events,
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
