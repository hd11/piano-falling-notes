import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate falling notes piano video from MusicXML'
    )
    # Web server mode (mutually exclusive with input file)
    parser.add_argument('input', nargs='?', default=None, help='MusicXML file path (omit when using --web)')
    parser.add_argument('-o', '--output', default=None, help='Output MP4 path (default: <input_name>.mp4)')
    parser.add_argument('--config', default=None, help='YAML config file path')
    parser.add_argument('--width', type=int, default=None)
    parser.add_argument('--height', type=int, default=None)
    parser.add_argument('--fps', type=int, default=None)
    parser.add_argument('--crf', type=int, default=None)
    parser.add_argument('--lookahead', type=float, default=None, dest='lookahead_seconds')
    parser.add_argument('--color-mode', default=None, choices=['pitch_range', 'rainbow_octave', 'part_based'])
    parser.add_argument('--theme', default=None, choices=['auto', 'classic', 'midnight', 'sunset', 'ocean', 'neon', 'pastel'])
    parser.add_argument('--background', default=None, help='Custom background color hex (e.g. #0F0F14)')
    parser.add_argument('--no-glow', action='store_true', help='Disable glow effects')
    parser.add_argument('--no-audio', action='store_true', help='Disable audio generation')
    parser.add_argument('--glow-intensity', type=float, default=None)
    # Web server options
    parser.add_argument('--web', action='store_true', help='Start web UI server')
    parser.add_argument('--port', type=int, default=5000, help='Port for web server (default: 5000)')
    parser.add_argument('--host', default='127.0.0.1', help='Host for web server (default: 127.0.0.1)')
    return parser.parse_args()
