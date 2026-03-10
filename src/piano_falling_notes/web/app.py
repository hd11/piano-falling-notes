import os
import re
import uuid
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = '/tmp/piano-falling-notes/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/piano-falling-notes/output'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# Ensure directories exist
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(parents=True, exist_ok=True)

# Job tracking: {job_id: {status, progress, total_frames, output_path, error, created_at}}
jobs = {}
jobs_lock = threading.Lock()

# Bounded thread pool for conversion jobs (max 3 concurrent)
MAX_CONCURRENT_JOBS = int(os.environ.get('MAX_CONCURRENT_JOBS', '3'))
executor_pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS)

# UUID validation pattern
_UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def _parse_hex_color(hex_str):
    """Parse '#RRGGBB' string to (R, G, B) tuple. Returns None if invalid."""
    if hex_str and hex_str.startswith('#') and len(hex_str) == 7:
        h = hex_str.lstrip('#')
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return None


def _parse_config_from_form(form):
    """Parse web form fields into Config, matching CLI options."""
    from ..core.config import Config
    config = Config()
    config.theme = "classic"  # hardcoded, no theme selector in web UI

    # --width / --height (resolution)
    resolution = form.get('resolution', '1080p')
    if resolution == '720p':
        config.width = 1280
        config.height = 720
    else:
        config.width = 1920
        config.height = 1080

    # --fps
    config.fps = 30 if form.get('fps', '60') == '30' else 60

    # --color-mode
    color_mode = form.get('color_mode', 'key_type')
    if color_mode in ('single', 'rainbow', 'neon', 'part', 'key_type'):
        config.color_mode = color_mode

    # --note-color
    c = _parse_hex_color(form.get('single_note_color', '').strip())
    if c:
        config.single_note_color = c

    # --white-key-color
    c = _parse_hex_color(form.get('white_key_note_color', '').strip())
    if c:
        config.white_key_note_color = c

    # --black-key-color
    c = _parse_hex_color(form.get('black_key_note_color', '').strip())
    if c:
        config.black_key_note_color = c

    # --background
    c = _parse_hex_color(form.get('background', '').strip())
    if c:
        config.custom_background = c

    # Effect toggles (CLI: --no-* flags)
    config.energy_color = (form.get('energy_color', 'on') == 'on')
    config.comet_effect = (form.get('comet_effect', 'on') == 'on')
    config.starflow = (form.get('starflow', 'on') == 'on')
    config.neon_burst = (form.get('neon_burst', 'on') == 'on')
    config.glow_enabled = (form.get('glow', 'on') == 'on')
    config.guide_lines = (form.get('guide_lines', 'on') == 'on')
    config.glitter = (form.get('glitter', 'off') == 'on')

    # --no-audio
    config.no_audio = (form.get('audio', 'on') != 'on')

    # --reverb
    config.reverb = (form.get('reverb', 'off') == 'on')

    # --vertical
    config.vertical = (form.get('vertical', 'off') == 'on')
    if config.vertical:
        # Swap to portrait dimensions
        if resolution == '720p':
            config.width = 720
            config.height = 1280
        else:
            config.width = 1080
            config.height = 1920

    # --velocity-effect
    config.velocity_effect = (form.get('velocity_effect', 'off') == 'on')

    # --pedal
    config.pedal = (form.get('pedal', 'off') == 'on')

    return config


def cleanup_old_jobs():
    """Remove jobs and files older than 1 hour."""
    cutoff = time.time() - 3600
    with jobs_lock:
        to_delete = [jid for jid, j in jobs.items() if j.get('created_at', 0) < cutoff]
        for jid in to_delete:
            job = jobs.pop(jid)
            for key in ('output_path', 'input_path'):
                path = job.get(key)
                if path:
                    Path(path).unlink(missing_ok=True)


def run_conversion(job_id, input_path, config):
    """Background conversion task."""
    from ..parser.musicxml_parser import parse_musicxml
    from ..timeline.builder import build_timeline
    from ..timeline.time_index import TimeIndex
    from ..rendering.layout import Layout
    from ..rendering.keyboard import KeyboardRenderer
    from ..rendering.notes import FallingNotesRenderer
    from ..rendering.effects import VisualEffects
    from ..rendering.colors import ColorScheme
    from ..rendering.themes import THEMES
    from ..export.video_writer import VideoWriter
    from ..export.audio import generate_audio, mux_video_audio
    from ..core.renderer import compute_energy_profile, render_frame, make_background_frame
    from PIL import Image

    def update(status, progress=None, total_frames=None):
        with jobs_lock:
            jobs[job_id]['status'] = status
            if progress is not None:
                jobs[job_id]['progress'] = progress
            if total_frames is not None:
                jobs[job_id]['total_frames'] = total_frames

    try:
        update('parsing', progress=0)

        # 1. Parse
        notes, metadata = parse_musicxml(input_path)

        # 2. Build timeline
        timeline = build_timeline(notes, metadata)
        time_index = TimeIndex(timeline.notes)

        update('rendering', progress=0)

        # 3. Use classic theme palette (no theme selector in web UI)
        theme = THEMES["classic"]
        bg = config.custom_background if config.custom_background else theme.background_color
        config.background_color = bg

        # Adjust keyboard ratio for vertical mode
        if config.vertical:
            config.keyboard_height_ratio = 0.10

        # Load background image if specified
        background_img = None
        if config.background_image:
            try:
                background_img = Image.open(config.background_image).convert('RGB')
                background_img = background_img.resize(
                    (config.width, config.height), Image.LANCZOS
                )
            except Exception:
                background_img = None

        # 4. Setup rendering
        layout = Layout(
            width=config.width,
            height=config.height,
            fps=config.fps,
            keyboard_height_ratio=config.keyboard_height_ratio,
            lookahead_seconds=config.lookahead_seconds,
        )
        color_scheme = ColorScheme(mode=config.color_mode, palette=theme.palette,
                                   single_color=config.single_note_color,
                                   white_key_note_color=config.white_key_note_color,
                                   black_key_note_color=config.black_key_note_color)
        keyboard = KeyboardRenderer(layout, color_scheme)
        falling = FallingNotesRenderer(layout, color_scheme, keyboard.keys,
                                       note_duration_ratio=config.note_duration_ratio,
                                       guide_lines=config.guide_lines,
                                       glitter=config.glitter,
                                       velocity_effect=config.velocity_effect)
        effects = VisualEffects()

        # 5. Calculate total frames
        lead_in = config.lead_in_seconds
        total_time = timeline.total_duration + lead_in + config.tail_seconds
        total_frames = int(total_time * layout.fps)
        update('rendering', progress=0, total_frames=total_frames)

        # 6. Generate audio
        audio_path = None
        if config.audio_file and Path(config.audio_file).exists():
            # Use external audio file directly
            audio_path = config.audio_file
        elif not config.no_audio:
            try:
                update('audio', progress=0)
                stem = Path(input_path).stem
                audio_path = str(Path(app.config['OUTPUT_FOLDER']) / f'{stem}_{job_id}.wav')
                project_root_path = str(Path(__file__).resolve().parents[3])
                generate_audio(input_path, audio_path, project_root_path,
                               soundfont_path=config.soundfont if config.soundfont else None,
                               reverb=config.reverb)
            except Exception as e:
                audio_path = None

        update('rendering', progress=0)

        # 7. Render video frames
        stem = Path(input_path).stem
        output_path = str(Path(app.config['OUTPUT_FOLDER']) / f'{stem}_{job_id}.mp4')

        if audio_path:
            video_only_path = str(Path(app.config['OUTPUT_FOLDER']) / f'{stem}_{job_id}_video.mp4')
        else:
            video_only_path = output_path

        # Pre-compute energy profile
        _energy = compute_energy_profile(timeline.notes, timeline.total_duration) if config.energy_color else {}

        prev_active = {}
        with VideoWriter(video_only_path, layout.width, layout.height, layout.fps, config.crf) as writer:
            for frame_idx in range(total_frames):
                current_time = frame_idx / layout.fps - lead_in
                frame = make_background_frame(layout, config, background_img)
                frame, prev_active = render_frame(
                    frame, layout, color_scheme, falling, keyboard, effects,
                    time_index, current_time, config, _energy, metadata, prev_active
                )
                writer.write_frame(frame)
                if frame_idx % 30 == 0:
                    update('rendering', progress=frame_idx)

        update('encoding', progress=total_frames)

        # 8. Mux audio
        if audio_path:
            mux_video_audio(video_only_path, audio_path, output_path, audio_offset=lead_in)
            Path(video_only_path).unlink(missing_ok=True)
            # Don't delete user-provided external audio file
            if not config.audio_file:
                Path(audio_path).unlink(missing_ok=True)

        with jobs_lock:
            jobs[job_id]['status'] = 'done'
            jobs[job_id]['progress'] = total_frames
            jobs[job_id]['output_path'] = output_path

        Path(input_path).unlink(missing_ok=True)

    except Exception as e:
        error_msg = str(e)
        if '/' in error_msg or '\\' in error_msg:
            error_msg = "Conversion failed. Please check your input file."
        with jobs_lock:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = error_msg
        Path(input_path).unlink(missing_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    cleanup_old_jobs()

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ('.musicxml', '.mxl', '.xml', '.mid', '.midi'):
        return jsonify({'error': 'Invalid file type. Upload a .musicxml, .mxl, or .mid file'}), 400

    job_id = str(uuid.uuid4())
    safe_name = f'{job_id}{ext}'
    input_path = str(Path(app.config['UPLOAD_FOLDER']) / safe_name)
    f.save(input_path)

    config = _parse_config_from_form(request.form)
    config.input_path = input_path

    # Handle audio file upload
    if 'audio_file' in request.files:
        af = request.files['audio_file']
        if af.filename:
            af_ext = Path(af.filename).suffix.lower()
            if af_ext in ('.mp3', '.wav', '.ogg', '.flac', '.m4a'):
                af_path = str(Path(app.config['UPLOAD_FOLDER']) / f'{job_id}_audio{af_ext}')
                af.save(af_path)
                config.audio_file = af_path

    # Handle background image upload
    if 'background_image' in request.files:
        bi = request.files['background_image']
        if bi.filename:
            bi_ext = Path(bi.filename).suffix.lower()
            if bi_ext in ('.jpg', '.jpeg', '.png', '.webp'):
                bi_path = str(Path(app.config['UPLOAD_FOLDER']) / f'{job_id}_bg{bi_ext}')
                bi.save(bi_path)
                config.background_image = bi_path

    # Handle soundfont upload
    if 'soundfont' in request.files:
        sf = request.files['soundfont']
        if sf.filename:
            sf_ext = Path(sf.filename).suffix.lower()
            if sf_ext in ('.sf2', '.sf3'):
                sf_path = str(Path(app.config['UPLOAD_FOLDER']) / f'{job_id}_sf{sf_ext}')
                sf.save(sf_path)
                config.soundfont = sf_path

    stem = Path(f.filename).stem
    config.output_path = str(Path(app.config['OUTPUT_FOLDER']) / f'{stem}_{job_id}.mp4')

    with jobs_lock:
        jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'total_frames': 0,
            'output_path': None,
            'input_path': input_path,
            'original_filename': f.filename,
            'error': None,
            'created_at': time.time(),
        }

    executor_pool.submit(run_conversion, job_id, input_path, config)

    return jsonify({'job_id': job_id})


@app.route('/preview', methods=['POST'])
def preview():
    """Generate a single preview frame image."""
    cleanup_old_jobs()

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ('.musicxml', '.mxl', '.xml', '.mid', '.midi'):
        return jsonify({'error': 'Invalid file type'}), 400

    preview_id = str(uuid.uuid4())
    safe_name = f'{preview_id}{ext}'
    input_path = str(Path(app.config['UPLOAD_FOLDER']) / safe_name)
    f.save(input_path)

    try:
        from ..parser.musicxml_parser import parse_musicxml
        from ..timeline.builder import build_timeline
        from ..timeline.time_index import TimeIndex
        from ..rendering.layout import Layout
        from ..rendering.keyboard import KeyboardRenderer
        from ..rendering.notes import FallingNotesRenderer
        from ..rendering.effects import VisualEffects
        from ..rendering.colors import ColorScheme
        from ..rendering.themes import THEMES
        from ..core.renderer import compute_energy_profile, render_frame, make_background_frame
        from PIL import Image
        import io

        config = _parse_config_from_form(request.form)
        config.input_path = input_path

        # Preview dimensions: smaller for speed, respect vertical
        if config.vertical:
            config.width = 540
            config.height = 960
            config.keyboard_height_ratio = 0.10
        else:
            config.width = 960
            config.height = 540

        # Handle background image for preview
        bg_img_preview = None
        if 'background_image' in request.files:
            bi = request.files['background_image']
            if bi.filename:
                bi_ext = Path(bi.filename).suffix.lower()
                if bi_ext in ('.jpg', '.jpeg', '.png', '.webp'):
                    bi_path = str(Path(app.config['UPLOAD_FOLDER']) / f'{preview_id}_bg{bi_ext}')
                    bi.save(bi_path)
                    try:
                        bg_img_preview = Image.open(bi_path).convert('RGB')
                        bg_img_preview = bg_img_preview.resize(
                            (config.width, config.height), Image.LANCZOS
                        )
                    except Exception:
                        bg_img_preview = None
                    finally:
                        Path(bi_path).unlink(missing_ok=True)

        # Parse and build
        notes, metadata = parse_musicxml(input_path)
        timeline = build_timeline(notes, metadata)
        time_index = TimeIndex(timeline.notes)

        # Use classic theme palette
        theme = THEMES["classic"]
        bg = config.custom_background if config.custom_background else theme.background_color
        config.background_color = bg

        layout = Layout(width=config.width, height=config.height, fps=30,
                        keyboard_height_ratio=config.keyboard_height_ratio,
                        lookahead_seconds=config.lookahead_seconds)
        color_scheme = ColorScheme(mode=config.color_mode, palette=theme.palette,
                                   single_color=config.single_note_color,
                                   white_key_note_color=config.white_key_note_color,
                                   black_key_note_color=config.black_key_note_color)
        keyboard = KeyboardRenderer(layout, color_scheme)
        falling = FallingNotesRenderer(layout, color_scheme, keyboard.keys,
                                       note_duration_ratio=config.note_duration_ratio,
                                       guide_lines=config.guide_lines,
                                       glitter=config.glitter,
                                       velocity_effect=config.velocity_effect)
        effects = VisualEffects()

        # Timeline scrubber: preview_time (0.0-1.0 ratio), default 0.1
        preview_time_ratio = 0.1
        try:
            pt = float(request.form.get('preview_time', '0.1'))
            if 0.0 <= pt <= 1.0:
                preview_time_ratio = pt
        except (ValueError, TypeError):
            pass
        target_time = timeline.total_duration * preview_time_ratio
        for t_try in [target_time, target_time + 2, target_time + 5, 5.0, 10.0]:
            view_start = t_try
            view_end = t_try + layout.lookahead_seconds
            visible = time_index.query(view_start, view_end)
            active = {}
            for n in visible:
                if n.start_seconds <= t_try < n.start_seconds + n.duration_seconds * config.note_duration_ratio:
                    active[n.midi_number] = n.velocity
            if active:
                break

        current_time = t_try

        # Energy profile and render using shared pipeline
        _energy = compute_energy_profile(timeline.notes, timeline.total_duration) if config.energy_color else {}
        frame = make_background_frame(layout, config, bg_img_preview)
        frame, _ = render_frame(
            frame, layout, color_scheme, falling, keyboard, effects,
            time_index, current_time, config, _energy, metadata, {}
        )

        # Save to bytes
        buf = io.BytesIO()
        frame.save(buf, format='PNG', optimize=True)
        buf.seek(0)

        return send_file(buf, mimetype='image/png', download_name='preview.png')

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        Path(input_path).unlink(missing_ok=True)


def _validate_job_id(job_id: str) -> bool:
    return bool(_UUID_RE.match(job_id))


@app.route('/status/<job_id>')
def status(job_id):
    if not _validate_job_id(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            return jsonify({'error': 'Job not found'}), 404
        job_status = job['status']
        job_progress = job['progress']
        job_total = job.get('total_frames', 0)
        job_error = job.get('error')

    progress_pct = 0
    if job_total > 0:
        progress_pct = min(100, int(job_progress / job_total * 100))
    elif job_status == 'done':
        progress_pct = 100

    resp = {
        'status': job_status,
        'progress': progress_pct,
    }
    if job_status == 'done':
        resp['output_url'] = f'/download/{job_id}'
    if job_status == 'error':
        resp['error'] = job_error or 'Unknown error'
    return jsonify(resp)


@app.route('/download/<job_id>')
def download(job_id):
    if not _validate_job_id(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    if job['status'] != 'done':
        return jsonify({'error': 'Not ready'}), 400
    output_path = job.get('output_path')
    if not output_path or not Path(output_path).exists():
        return jsonify({'error': 'Output file missing'}), 404

    original = job.get('original_filename', '')
    if original:
        download_name = Path(original).stem + '.mp4'
    else:
        download_name = Path(output_path).name

    return send_file(output_path, as_attachment=True, download_name=download_name)


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
