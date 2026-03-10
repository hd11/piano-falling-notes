# AGENTS.md - web

Parent: ../AGENTS.md

Web UI package — Flask-based browser interface for score-to-video conversion and preview.

## Files

### app.py

Flask application: file upload, config form parsing, video conversion endpoint, live preview with Server-Sent Events.

**Key configuration:**
- `UPLOAD_FOLDER` — /tmp/piano-falling-notes/uploads (max 50 MB per file)
- `OUTPUT_FOLDER` — /tmp/piano-falling-notes/output
- `MAX_CONTENT_LENGTH` — 50 MB upload limit
- `MAX_CONCURRENT_JOBS` — 3 concurrent conversion jobs (environment variable)

**Job tracking:**
- `jobs: dict[job_id, {status, progress, total_frames, output_path, error, created_at}]` — Thread-safe job state
- `jobs_lock` — Threading lock for concurrent access
- `executor_pool` — ThreadPoolExecutor (bounded max_workers)

**Key functions:**

- `_parse_hex_color(hex_str) -> tuple[int, int, int] | None` — Parse '#RRGGBB' string to RGB tuple

- `_parse_config_from_form(form) -> Config` — Parse web form fields into Config object
  - Resolution: '720p' (1280×720) or '1080p' (1920×1080)
  - FPS: 30 or 60
  - Color mode: single, rainbow, neon, part, key_type
  - Custom colors: single_note_color, white_key_note_color, black_key_note_color, background (hex)
  - Effect toggles (form 'on'/'off' strings): energy_color, comet_effect, starflow, neon_burst, glow, guide_lines, glitter
  - Flags: no_audio, reverb, vertical (portrait), velocity_effect, pedal, key_depression, comet_trail_glow
  - Returns Config with form values applied

- `cleanup_old_jobs()` — Remove jobs and files older than 1 hour

- `run_conversion(job_id, input_path, config)` — Background conversion task (runs in thread pool)
  1. Parse MusicXML with musicxml_parser
  2. Build timeline with timeline.builder
  3. Create TimeIndex for fast note queries
  4. Initialize Layout, KeyboardRenderer, FallingNotesRenderer, VisualEffects, ColorScheme
  5. Generate audio (optional)
  6. Render video frame-by-frame
  7. Mux audio with video
  8. Update job status

**Flask endpoints (defined in full app.py):**
- `GET /` — Render index.html (form + preview)
- `POST /upload` — Accept score file, validate, return upload_folder path
- `POST /convert` — Submit conversion job, return job_id
- `GET /job/<job_id>` — Poll job status (JSON)
- `GET /download/<job_id>` — Download output video file
- `GET /stream/<job_id>` — Server-Sent Events stream of job progress

**Web form parsing:** Config is parsed from request.form with string comparisons ('on'/'off'). Form field names map directly to Config attributes.

### templates/index.html

Jinja2 HTML template with Korean UI labels and real-time preview controls.

**Features:**
- File upload input (accept .mxl, .xml, .mid, .midi)
- Resolution selector: 720p, 1080p
- FPS selector: 30, 60
- Color mode dropdown: single, rainbow, neon, part, key_type
- Color pickers: single note, white key, black key, background
- Effect toggle switches: energy_color, comet_effect, starflow, neon_burst, glow, guide_lines, glitter
- Audio options: audio on/off, reverb on/off
- Layout options: vertical (portrait) on/off
- Advanced options: velocity_effect, pedal, key_depression, comet_trail_glow
- Job progress bar with frame counter
- Download button for completed videos
- Live preview (Server-Sent Events polling)

**Labels:** All UI labels are in Korean (e.g., "파일 선택" for file upload, "품질" for quality).

**Form submission:**
- POST to /convert with FormData (file + config)
- Receive job_id
- Poll /job/<job_id> for progress
- Stream events via /stream/<job_id> for live updates

## Integration Notes

- Web UI duplicates render pipeline calls (run_conversion) — maintains parity with CLI
- Config parsing converts form strings ('on'/'off') to boolean attributes
- Job tracking uses dict with threading.Lock for concurrent conversions
- Old jobs/files automatically cleaned up after 1 hour
- Template uses Jinja2 templating with inline JavaScript for form handling and SSE
- Korean labels preserve regional user experience; do not translate to English
- Background jobs run in thread pool; Flask endpoints return immediately with job_id
