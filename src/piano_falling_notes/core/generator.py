import tempfile
from pathlib import Path

from PIL import Image
from tqdm import tqdm
from ..parser.musicxml_parser import parse_musicxml
from ..timeline.builder import build_timeline
from ..timeline.time_index import TimeIndex
from ..rendering.layout import Layout
from ..rendering.keyboard import KeyboardRenderer
from ..rendering.notes import FallingNotesRenderer
from ..rendering.effects import VisualEffects
from ..rendering.colors import ColorScheme
from ..rendering.themes import THEMES, auto_select_theme
from ..export.video_writer import VideoWriter
from ..export.audio import generate_audio, mux_video_audio
from .config import Config


class VideoGenerator:
    def generate(self, config: Config) -> str:
        """Generate falling notes video with audio. Returns output path."""
        # 1. Parse MusicXML
        print(f"Parsing: {config.input_path}")
        notes, metadata = parse_musicxml(config.input_path)
        print(f"  Found {len(notes)} notes, tempo={metadata['tempo_bpm']} BPM")

        # 2. Build timeline
        timeline = build_timeline(notes, metadata)
        time_index = TimeIndex(timeline.notes)
        print(f"  Timeline: {timeline.total_duration:.1f}s, {len(timeline.notes)} render notes")

        # 3. Apply theme
        if config.theme == "auto":
            theme = auto_select_theme(metadata)
            print(f"  Auto theme: {theme.label} (key={metadata.get('key_signature', '?')}, tempo={metadata['tempo_bpm']})")
        elif config.theme in THEMES:
            theme = THEMES[config.theme]
            print(f"  Theme: {theme.label}")
        else:
            theme = THEMES["classic"]

        bg = config.custom_background if config.custom_background else theme.background_color
        config.background_color = bg

        # 4. Setup rendering
        layout = Layout(
            width=config.width, height=config.height, fps=config.fps,
            keyboard_height_ratio=config.keyboard_height_ratio,
            lookahead_seconds=config.lookahead_seconds,
        )
        color_scheme = ColorScheme(mode=config.color_mode, palette=theme.palette, single_color=config.single_note_color, white_key_note_color=config.white_key_note_color, black_key_note_color=config.black_key_note_color)
        keyboard = KeyboardRenderer(layout, color_scheme)
        falling = FallingNotesRenderer(layout, color_scheme, keyboard.keys,
                                       note_duration_ratio=config.note_duration_ratio,
                                       guide_lines=config.guide_lines,
                                       glitter=config.glitter)
        effects = VisualEffects()

        # 4. Calculate total frames
        lead_in = config.lead_in_seconds
        total_time = timeline.total_duration + lead_in + config.tail_seconds
        total_frames = int(total_time * layout.fps)

        # 5. Generate audio
        audio_path = None
        if not config.no_audio:
            try:
                print("Generating audio...")
                audio_path = str(Path(config.output_path).with_suffix('.wav'))
                project_root = str(Path(__file__).resolve().parents[3])
                generate_audio(config.input_path, audio_path, project_root)
                print(f"  Audio: {audio_path}")
            except Exception as e:
                print(f"  Audio generation failed: {e}")
                print("  Continuing without audio...")
                audio_path = None

        # 6. Render video frames
        # If we have audio, render to temp file first, then mux
        if audio_path:
            video_only_path = str(Path(config.output_path).with_suffix('.video_only.mp4'))
        else:
            video_only_path = config.output_path

        print(f"Rendering {total_frames} frames ({total_time:.1f}s @ {layout.fps}fps)...")

        prev_active = {}  # {midi: start_seconds} of last frame's active notes
        with VideoWriter(video_only_path, layout.width, layout.height, layout.fps, config.crf) as writer:
            for frame_idx in tqdm(range(total_frames), desc="Rendering"):
                current_time = frame_idx / layout.fps - lead_in

                # Background
                frame = Image.new('RGB', (layout.width, layout.height), config.background_color)

                # Query visible notes
                view_start = current_time
                view_end = current_time + layout.lookahead_seconds
                visible = time_index.query(view_start, view_end)

                # Draw falling notes
                frame = falling.render(frame, visible, current_time)

                # Find currently playing notes (for keyboard highlighting)
                # Apply note_duration_ratio so repeated notes show a release gap
                active = {}
                active_starts = {}  # {midi: start_seconds} to identify specific note instance
                for n in visible:
                    if n.start_seconds <= current_time < n.start_seconds + n.duration_seconds * config.note_duration_ratio:
                        active[n.midi_number] = n.velocity
                        active_starts[n.midi_number] = n.start_seconds

                # Newly struck = new midi OR same midi but different note (re-strike)
                newly_active = {}
                for m, v in active.items():
                    if m not in prev_active or active_starts[m] != prev_active[m]:
                        newly_active[m] = v

                # Ascending bubble particles around active notes
                frame = effects.apply_ascending_bubbles(
                    frame, visible, active, keyboard.keys,
                    layout.keyboard_top, color_scheme, current_time,
                )

                # Firefly ascent on note strike
                if newly_active:
                    frame = effects.apply_firefly_ascent(
                        frame, newly_active, keyboard.keys,
                        layout.keyboard_top, color_scheme, current_time,
                    )

                # Ambient starflow (every frame)
                frame = effects.apply_starflow(
                    frame, active, keyboard.keys,
                    layout.keyboard_top, color_scheme, current_time,
                )

                # Keyboard-top glow for active notes
                frame = effects.apply_note_glow(
                    frame, active, keyboard.keys,
                    layout.keyboard_top, color_scheme, current_time,
                )

                # Render keyboard (paste at bottom)
                kb_img = keyboard.render(active)
                frame.paste(kb_img, (0, layout.keyboard_top))

                writer.write_frame(frame)
                prev_active = active_starts

        # 7. Mux audio if available
        if audio_path:
            print("Muxing video + audio...")
            mux_video_audio(video_only_path, audio_path, config.output_path,
                            audio_offset=lead_in)
            # Cleanup temp files
            Path(video_only_path).unlink(missing_ok=True)
            Path(audio_path).unlink(missing_ok=True)

        print(f"Done! Output: {config.output_path}")
        return config.output_path
