# AGENTS.md - export

Parent: ../AGENTS.md

Export package — video and audio output.

## Files

### audio.py

Audio synthesis using music21 MIDI to WAV via FluidSynth, or external audio file attachment.

**Key functions:**
- `find_soundfont(project_root)` — Locate .sf2 soundfont file from search paths or system locations
- `musicxml_to_midi(musicxml_path, midi_path)` — Convert MusicXML to MIDI using music21; forces program 0 (Acoustic Grand Piano)
- `midi_to_wav(midi_path, wav_path, soundfont_path, sample_rate=44100, reverb=False)` — Synthesize MIDI to WAV using fluidsynth CLI
- `mux_video_audio(video_path, audio_path, output_path, audio_offset=0.0)` — Combine video and audio with FFmpeg; supports audio delay offset
- `generate_audio(musicxml_path, wav_path, project_root=".", soundfont_path=None, reverb=False)` — Full pipeline: MusicXML → MIDI → WAV

**Soundfont search order:**
1. config/TimGM6mb.sf2
2. config/GeneralUser_GS.sf2
3. /usr/share/sounds/sf2/FluidR3_GM.sf2
4. /usr/share/soundfonts/FluidR3_GM.sf2
5. Linuxbrew installation paths

**Error handling:** Raises RuntimeError if fluidsynth not found, soundfont missing, or FFmpeg mux fails.

### video_writer.py

VideoWriter context manager wrapping FFmpeg subprocess pipe for frame writing and audio muxing.

**Key class:**
- `VideoWriter(output_path, width, height, fps=60, crf=18)` — Context manager
  - `__init__()` — Start FFmpeg process with stdin pipe (rawvideo format, libx264 codec)
  - `write_frame(frame: Image.Image)` — Write one PIL Image as raw RGB bytes to FFmpeg stdin
  - `close()` — Finalize encoding, check returncode for errors
  - `__enter__() / __exit__()` — Context manager support

**Key detail:** `__exit__` checks returncode only if no exception occurred; suppresses BrokenPipeError on stdin close.

**FFmpeg command structure:**
```
ffmpeg -y -f rawvideo -vcodec rawvideo -pix_fmt rgb24 \
  -s WIDTHxHEIGHT -r FPS -i - \
  -c:v libx264 -preset medium -crf CRF -pix_fmt yuv420p -movflags +faststart \
  output_path
```

**Error handling:** Raises RuntimeError if FFmpeg subprocess exits with non-zero returncode.

## Integration Notes

- Audio generation is optional (--no-audio flag skips it)
- Video encoding uses medium preset (quality/speed balance)
- CRF 18 is high quality; typical range 18–28
- Audio offset supports audio delay synchronization with video
- Both modules use subprocess.run/Popen with capture_output for error detection
