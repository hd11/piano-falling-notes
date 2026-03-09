from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Config:
    # I/O
    input_path: str = ""
    output_path: str = "output.mp4"

    # Video
    width: int = 1920
    height: int = 1080
    fps: int = 60
    crf: int = 18

    # Layout
    keyboard_height_ratio: float = 0.15
    lookahead_seconds: float = 3.0

    # Colors
    background_color: tuple = (15, 15, 20)
    color_mode: str = "single"  # options: single, rainbow, neon, part, key_type
    single_note_color: tuple = (0, 255, 200)  # neon cyan default
    white_key_note_color: tuple = (0, 255, 128)  # green neon (key_type mode)
    black_key_note_color: tuple = (0, 128, 255)  # blue neon (key_type mode)
    note_opacity: float = 0.95
    theme: str = "auto"
    custom_background: tuple | None = None

    # Keyboard
    white_key_color: tuple = (240, 240, 240)
    black_key_color: tuple = (30, 30, 30)
    active_key_glow: bool = True

    # Effects
    glow_enabled: bool = True
    glow_intensity: float = 0.7
    particles_enabled: bool = False
    note_border_radius: float = 4.0
    neon_burst: bool = True  # neon burst on key strike
    guide_lines: bool = True  # background guide lines
    note_style: str = "standard"  # "standard" or "djeq" (DJ EQ Max visualization)
    note_duration_ratio: float = 0.92  # visual shortening ratio for note separation
    glitter: bool = False  # twinkling glitter on note bars
    comet_effect: bool = True  # comet/shooting-star effect
    energy_color: bool = True  # energy-based dynamic note color
    starflow: bool = True  # ambient starflow background effect

    # Timing
    lead_in_seconds: float = 2.0
    tail_seconds: float = 2.0

    # Audio
    no_audio: bool = False
    audio_file: str = ""        # external audio file path (skip synthesis)
    soundfont: str = ""         # custom soundfont path (.sf2/.sf3)
    reverb: bool = False        # enable fluidsynth reverb

    # Layout modes
    vertical: bool = False      # vertical (portrait) video mode

    # Background
    background_image: str = ""  # background image path

    # Note rendering
    velocity_effect: bool = False  # velocity-based brightness scaling

    # Pedal
    pedal: bool = False         # sustain pedal visualization

    # Piano range
    piano_range: tuple = (21, 108)

    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        with open(path) as f:
            data = yaml.safe_load(f)
        # Handle tuple fields that come as lists from YAML
        for key in ('background_color', 'white_key_color', 'black_key_color', 'piano_range', 'single_note_color', 'white_key_note_color', 'black_key_note_color'):
            if key in data and isinstance(data[key], list):
                data[key] = tuple(data[key])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_cli_and_yaml(cls, cli_args, yaml_path: Optional[str] = None) -> 'Config':
        config = cls.from_yaml(yaml_path) if yaml_path else cls()
        for key, value in vars(cli_args).items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)
        return config
