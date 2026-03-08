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
    color_mode: str = "rainbow_octave"
    note_opacity: float = 0.95

    # Keyboard
    white_key_color: tuple = (240, 240, 240)
    black_key_color: tuple = (30, 30, 30)
    active_key_glow: bool = True

    # Effects
    glow_enabled: bool = True
    glow_intensity: float = 0.7
    particles_enabled: bool = False
    note_border_radius: float = 4.0

    # Timing
    lead_in_seconds: float = 2.0
    tail_seconds: float = 2.0

    # Audio
    no_audio: bool = False

    # Piano range
    piano_range: tuple = (21, 108)

    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        with open(path) as f:
            data = yaml.safe_load(f)
        # Handle tuple fields that come as lists from YAML
        for key in ('background_color', 'white_key_color', 'black_key_color', 'piano_range'):
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
