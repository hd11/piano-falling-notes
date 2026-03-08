import os
import uuid
import threading
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = '/tmp/piano-falling-notes/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/piano-falling-notes/output'

# Ensure directories exist
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(parents=True, exist_ok=True)

# Job tracking: {job_id: {status, progress, total_frames, output_path, error, created_at}}
jobs = {}
jobs_lock = threading.Lock()


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
    """Background conversion thread."""
    import sys
    # Ensure the package is importable
    project_root = str(Path(__file__).resolve().parents[4])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

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
        from ..timeline.builder import build_timeline
        timeline = build_timeline(notes, metadata)
        time_index = TimeIndex(timeline.notes)

        update('rendering', progress=0)

        # 3. Setup rendering
        layout = Layout(
            width=config.width,
            height=config.height,
            fps=config.fps,
            keyboard_height_ratio=config.keyboard_height_ratio,
            lookahead_seconds=config.lookahead_seconds,
        )
        color_scheme = ColorScheme(mode=config.color_mode)
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
        with jobs_lock:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = str(e)
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

    t = threading.Thread(target=run_conversion, args=(job_id, input_path, config), daemon=True)
    t.start()

    return jsonify({'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if job is None:
        return jsonify({'error': 'Job not found'}), 404

    total = job.get('total_frames', 0)
    progress_pct = 0
    if total > 0:
        progress_pct = min(100, int(job['progress'] / total * 100))
    elif job['status'] == 'done':
        progress_pct = 100

    resp = {
        'status': job['status'],
        'progress': progress_pct,
    }
    if job['status'] == 'done':
        resp['output_url'] = f'/download/{job_id}'
    if job['status'] == 'error':
        resp['error'] = job.get('error', 'Unknown error')
    return jsonify(resp)


@app.route('/download/<job_id>')
def download(job_id):
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
