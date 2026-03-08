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
    from ..export.video_writer import VideoWriter
    from ..export.audio import generate_audio, mux_video_audio
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

        # 3. Apply theme
        from ..rendering.themes import THEMES, auto_select_theme
        if config.theme == "auto":
            theme = auto_select_theme(metadata)
        elif config.theme in THEMES:
            theme = THEMES[config.theme]
        else:
            theme = THEMES["classic"]

        bg = config.custom_background if config.custom_background else theme.background_color
        config.background_color = bg

        # 4. Setup rendering
        layout = Layout(
            width=config.width,
            height=config.height,
            fps=config.fps,
            keyboard_height_ratio=config.keyboard_height_ratio,
            lookahead_seconds=config.lookahead_seconds,
        )
        color_scheme = ColorScheme(mode=config.color_mode, palette=theme.palette)
        keyboard = KeyboardRenderer(layout, color_scheme)
        falling = FallingNotesRenderer(layout, color_scheme, keyboard.keys)
        effects = VisualEffects()

        # 4. Calculate total frames
        lead_in = config.lead_in_seconds
        total_time = timeline.total_duration + lead_in + config.tail_seconds
        total_frames = int(total_time * layout.fps)
        update('rendering', progress=0, total_frames=total_frames)

        # 5. Generate audio
        audio_path = None
        if not config.no_audio:
            try:
                update('audio', progress=0)
                stem = Path(input_path).stem
                audio_path = str(Path(app.config['OUTPUT_FOLDER']) / f'{stem}_{job_id}.wav')
                project_root_path = str(Path(__file__).resolve().parents[4])
                generate_audio(input_path, audio_path, project_root_path)
            except Exception as e:
                audio_path = None

        update('rendering', progress=0)

        # 6. Render video frames
        stem = Path(input_path).stem
        output_path = str(Path(app.config['OUTPUT_FOLDER']) / f'{stem}_{job_id}.mp4')

        if audio_path:
            video_only_path = str(Path(app.config['OUTPUT_FOLDER']) / f'{stem}_{job_id}_video.mp4')
        else:
            video_only_path = output_path

        with VideoWriter(video_only_path, layout.width, layout.height, layout.fps, config.crf) as writer:
            for frame_idx in range(total_frames):
                current_time = frame_idx / layout.fps - lead_in

                frame = Image.new('RGB', (layout.width, layout.height), config.background_color)

                view_start = current_time
                view_end = current_time + layout.lookahead_seconds
                visible = time_index.query(view_start, view_end)

                frame = falling.render(frame, visible, current_time)

                active = {}
                for n in visible:
                    if n.start_seconds <= current_time < n.start_seconds + n.duration_seconds:
                        active[n.midi_number] = n.velocity

                if config.glow_enabled and active:
                    frame = effects.apply_note_glow(
                        frame, active, keyboard.keys,
                        layout.keyboard_top, color_scheme,
                    )

                kb_img = keyboard.render(active)
                frame.paste(kb_img, (0, layout.keyboard_top))

                writer.write_frame(frame)

                # Update progress every 30 frames
                if frame_idx % 30 == 0:
                    update('rendering', progress=frame_idx)

        update('encoding', progress=total_frames)

        # 7. Mux audio
        if audio_path:
            mux_video_audio(video_only_path, audio_path, output_path, audio_offset=lead_in)
            Path(video_only_path).unlink(missing_ok=True)
            Path(audio_path).unlink(missing_ok=True)

        with jobs_lock:
            jobs[job_id]['status'] = 'done'
            jobs[job_id]['progress'] = total_frames
            jobs[job_id]['output_path'] = output_path

        # Clean up input file
        Path(input_path).unlink(missing_ok=True)

    except Exception as e:
        # Sanitize error: don't expose internal paths or stack traces
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
    if ext not in ('.musicxml', '.mxl', '.xml'):
        return jsonify({'error': 'Invalid file type. Upload a .musicxml or .mxl file'}), 400

    job_id = str(uuid.uuid4())
    safe_name = f'{job_id}{ext}'
    input_path = str(Path(app.config['UPLOAD_FOLDER']) / safe_name)
    f.save(input_path)

    # Parse options
    from ..core.config import Config
    config = Config()
    config.input_path = input_path

    color_mode = request.form.get('color_mode', 'rainbow_octave')
    if color_mode in ('rainbow_octave', 'pitch_range', 'part_based'):
        config.color_mode = color_mode

    theme = request.form.get('theme', 'auto')
    from ..rendering.themes import THEME_NAMES
    if theme in THEME_NAMES or theme == 'auto':
        config.theme = theme

    custom_bg = request.form.get('custom_bg', '').strip()
    if custom_bg and custom_bg.startswith('#') and len(custom_bg) == 7:
        h = custom_bg.lstrip('#')
        config.custom_background = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    resolution = request.form.get('resolution', '1080p')
    if resolution == '720p':
        config.width = 1280
        config.height = 720
    else:
        config.width = 1920
        config.height = 1080

    fps_val = request.form.get('fps', '60')
    config.fps = 30 if fps_val == '30' else 60

    glow = request.form.get('glow', 'on')
    config.glow_enabled = (glow == 'on')

    audio = request.form.get('audio', 'on')
    config.no_audio = (audio != 'on')

    stem = Path(f.filename).stem
    config.output_path = str(Path(app.config['OUTPUT_FOLDER']) / f'{stem}_{job_id}.mp4')

    with jobs_lock:
        jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'total_frames': 0,
            'output_path': None,
            'input_path': input_path,
            'error': None,
            'created_at': time.time(),
        }

    executor_pool.submit(run_conversion, job_id, input_path, config)

    return jsonify({'job_id': job_id})


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
        # Snapshot values under lock to avoid race conditions
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

    filename = Path(output_path).name
    # Strip the job_id suffix for a cleaner download name
    parts = filename.rsplit(f'_{job_id}', 1)
    download_name = parts[0] + '.mp4' if len(parts) == 2 else filename

    return send_file(output_path, as_attachment=True, download_name=download_name)


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
