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
from .renderer import compute_energy_profile, render_frame, make_background_frame


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

        # 4. Adjust keyboard ratio for vertical mode
        if config.vertical:
            config.keyboard_height_ratio = 0.10

        # 4a. Load background image if specified
        background_img = None
        if config.background_image:
            try:
                background_img = Image.open(config.background_image).convert('RGB')
                background_img = background_img.resize(
                    (config.width, config.height), Image.LANCZOS
                )
                print(f"  Background image: {config.background_image}")
            except Exception as e:
                print(f"  Background image load failed: {e}, using solid color")
                background_img = None

        # 4b. Setup rendering
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
                                       glitter=config.glitter,
                                       velocity_effect=config.velocity_effect)
        effects = VisualEffects()

        # 4. Calculate total frames
        lead_in = config.lead_in_seconds
        total_time = timeline.total_duration + lead_in + config.tail_seconds
        total_frames = int(total_time * layout.fps)

        # 5. Generate audio
        audio_path = None
        if config.audio_file and Path(config.audio_file).exists():
            # Use external audio file directly
            audio_path = config.audio_file
            print(f"  Using external audio: {audio_path}")
        elif not config.no_audio:
            try:
                print("Generating audio...")
                audio_path = str(Path(config.output_path).with_suffix('.wav'))
                project_root = str(Path(__file__).resolve().parents[3])
                generate_audio(config.input_path, audio_path, project_root,
                               soundfont_path=config.soundfont if config.soundfont else None,
                               reverb=config.reverb)
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

        # Pre-compute energy profile
        _energy = compute_energy_profile(timeline.notes, timeline.total_duration) if config.energy_color else {}

        prev_active = {}
        with VideoWriter(video_only_path, layout.width, layout.height, layout.fps, config.crf) as writer:
            for frame_idx in tqdm(range(total_frames), desc="Rendering"):
                current_time = frame_idx / layout.fps - lead_in
                frame = make_background_frame(layout, config, background_img)
                frame, prev_active = render_frame(
                    frame, layout, color_scheme, falling, keyboard, effects,
                    time_index, current_time, config, _energy, metadata, prev_active
                )
                writer.write_frame(frame)

        # 7. Mux audio if available
        if audio_path:
            print("Muxing video + audio...")
            mux_video_audio(video_only_path, audio_path, config.output_path,
                            audio_offset=lead_in)
            # Cleanup temp files
            Path(video_only_path).unlink(missing_ok=True)
            # Don't delete user-provided external audio file
            if not config.audio_file:
                Path(audio_path).unlink(missing_ok=True)

        print(f"Done! Output: {config.output_path}")
        return config.output_path
