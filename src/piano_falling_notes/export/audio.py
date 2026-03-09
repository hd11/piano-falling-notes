"""MusicXML → MIDI → WAV audio generation using music21 + fluidsynth."""

import subprocess
import shutil
import tempfile
from pathlib import Path


SOUNDFONT_SEARCH_PATHS = [
    "config/TimGM6mb.sf2",
    "config/GeneralUser_GS.sf2",
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
]


def find_soundfont(project_root: str = ".") -> str | None:
    """Find a usable .sf2 soundfont file."""
    for rel in SOUNDFONT_SEARCH_PATHS:
        p = Path(project_root) / rel
        if p.exists() and p.stat().st_size > 1000:
            return str(p)
    # Check fluidsynth default
    brew_sf = Path("/home/linuxbrew/.linuxbrew/Cellar/fluid-synth")
    if brew_sf.exists():
        for sf in brew_sf.rglob("*.sf2"):
            if sf.stat().st_size > 1000:
                return str(sf)
    return None


def musicxml_to_midi(musicxml_path: str, midi_path: str) -> str:
    """Convert MusicXML to MIDI using music21, forcing piano sound."""
    import music21
    score = music21.converter.parse(musicxml_path)
    mf = music21.midi.translate.streamToMidiFile(score)
    # Force program 0 (Acoustic Grand Piano) on tracks that have notes
    for track in mf.tracks:
        # Skip metadata-only tracks (no NOTE_ON events)
        has_notes = any(e.type == music21.midi.ChannelVoiceMessages.NOTE_ON
                        for e in track.events)
        if not has_notes:
            continue
        # Set existing PROGRAM_CHANGE to piano
        for event in track.events:
            if event.type == music21.midi.ChannelVoiceMessages.PROGRAM_CHANGE:
                event.data = 0  # Acoustic Grand Piano
    mf.open(midi_path, 'wb')
    mf.write()
    mf.close()
    return midi_path


def midi_to_wav(midi_path: str, wav_path: str, soundfont_path: str,
                sample_rate: int = 44100, reverb: bool = False) -> str:
    """Synthesize MIDI to WAV using fluidsynth."""
    fluidsynth = shutil.which("fluidsynth")
    if not fluidsynth:
        raise RuntimeError("fluidsynth not found. Install with: brew install fluidsynth")

    cmd = [fluidsynth, "-ni", "-F", wav_path, "-r", str(sample_rate)]
    if reverb:
        cmd += ["-o", "synth.reverb.active=1"]
    cmd += [soundfont_path, midi_path]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if not Path(wav_path).exists() or Path(wav_path).stat().st_size == 0:
        raise RuntimeError(f"fluidsynth failed: {result.stderr[-500:]}")
    return wav_path


def mux_video_audio(video_path: str, audio_path: str, output_path: str,
                    audio_offset: float = 0.0) -> str:
    """Combine video and audio with FFmpeg. audio_offset delays audio start."""
    cmd = ["ffmpeg", "-y", "-i", video_path]
    if audio_offset > 0:
        cmd += ["-itsoffset", str(audio_offset)]
    cmd += ["-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg mux failed: {result.stderr[-500:]}")
    return output_path


def generate_audio(musicxml_path: str, wav_path: str, project_root: str = ".",
                   soundfont_path: str | None = None, reverb: bool = False) -> str:
    """Full pipeline: MusicXML → MIDI → WAV."""
    if soundfont_path and Path(soundfont_path).exists():
        sf = soundfont_path
    else:
        sf = find_soundfont(project_root)
    if not sf:
        raise RuntimeError("No soundfont found. Place a .sf2 file in config/")

    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        midi_path = tmp.name

    print(f"  Generating audio with soundfont: {Path(sf).name}")
    musicxml_to_midi(musicxml_path, midi_path)
    midi_to_wav(midi_path, wav_path, sf, reverb=reverb)
    Path(midi_path).unlink(missing_ok=True)
    return wav_path
