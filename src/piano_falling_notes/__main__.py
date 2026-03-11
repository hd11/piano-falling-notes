from .cli import parse_args
from .core.config import Config
from .core.generator import VideoGenerator
from pathlib import Path


def main():
    args = parse_args()

    # Web server mode
    if args.web:
        from .web.app import app
        print(f"Starting Piano Falling Notes web server on http://{args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=False)
        return

    # CLI conversion mode
    if not args.input:
        print("Error: provide an input file or use --web to start the web UI.")
        raise SystemExit(1)

    # Build config
    config = Config.from_cli_and_yaml(args, args.config)
    config.input_path = args.input

    # Default output name
    if args.output:
        config.output_path = args.output
    else:
        config.output_path = str(Path(args.input).stem) + '.mp4'

    # Handle flags
    if args.no_glow:
        config.glow_enabled = False
    if args.no_audio:
        config.no_audio = True
    if args.color_mode:
        config.color_mode = args.color_mode
    if args.note_color:
        hex_str = args.note_color.lstrip('#')
        config.single_note_color = (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
    if args.white_key_color:
        hex_str = args.white_key_color.lstrip('#')
        config.white_key_note_color = (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
    if args.black_key_color:
        hex_str = args.black_key_color.lstrip('#')
        config.black_key_note_color = (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
    if args.no_water_splash:
        config.water_splash = False
    if args.no_guide_lines:
        config.guide_lines = False
    if args.glitter:
        config.glitter = True
    if args.no_comet:
        config.comet_effect = False
    if args.no_energy_color:
        config.energy_color = False
    if args.energy_mid_threshold is not None:
        config.energy_mid_threshold = args.energy_mid_threshold
    if args.energy_high_threshold is not None:
        config.energy_high_threshold = args.energy_high_threshold
    if args.no_starflow:
        config.starflow = False
    if args.theme:
        config.theme = args.theme
    if args.background:
        hex_str = args.background.lstrip('#')
        config.custom_background = (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
    if args.audio_file:
        config.audio_file = args.audio_file
    if args.soundfont:
        config.soundfont = args.soundfont
    if args.reverb:
        config.reverb = True
    if args.vertical:
        config.vertical = True
        # Swap to portrait defaults if user didn't specify dimensions
        if args.width is None and args.height is None:
            config.width = 1080
            config.height = 1920
    if args.background_image:
        config.background_image = args.background_image
    if args.velocity_effect:
        config.velocity_effect = True
    if args.pedal:
        config.pedal = True
    if args.key_depression:
        config.key_depression = True
    if args.comet_trail_glow:
        config.comet_trail_glow = True

    # Generate
    generator = VideoGenerator()
    generator.generate(config)


if __name__ == '__main__':
    main()
