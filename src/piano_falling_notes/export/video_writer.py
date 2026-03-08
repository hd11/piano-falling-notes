import subprocess
import numpy as np
from PIL import Image


class VideoWriter:
    def __init__(self, output_path: str, width: int, height: int, fps: int = 60, crf: int = 18):
        """Start FFmpeg process with stdin pipe."""
        self.process = subprocess.Popen(
            [
                'ffmpeg', '-y',
                '-f', 'rawvideo', '-vcodec', 'rawvideo',
                '-pix_fmt', 'rgb24',
                '-s', f'{width}x{height}',
                '-r', str(fps),
                '-i', '-',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', str(crf),
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                output_path,
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def write_frame(self, frame: Image.Image):
        """Write one PIL Image frame."""
        raw = np.array(frame.convert('RGB'))
        self.process.stdin.write(raw.tobytes())

    def close(self):
        """Finalize encoding."""
        self.process.stdin.close()
        self.process.wait()
        if self.process.returncode != 0:
            error = self.process.stderr.read().decode()
            raise RuntimeError(f"FFmpeg error: {error}")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
