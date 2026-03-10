"""Visual effects package — facade re-exporting VisualEffects."""

import numpy as np

from .ambient import AmbientEffectsMixin
from .burst import BurstEffectsMixin
from .particles import ParticleEffectsMixin


class VisualEffects(BurstEffectsMixin, ParticleEffectsMixin, AmbientEffectsMixin):
    def __init__(self):
        self._burst_state = {}  # {midi: {color, intensity, cx, key_w, ray_angles, ray_lengths, frame}}
        self._wave_phase = 0.0  # persistent wave phase counter
        self._bubble_particles = []  # list of particle dicts
        self._firefly_particles = []  # list of firefly particle dicts
        self._rise_cooldown = 0       # frames until next rise can spawn
        self._next_rise_time = 0.0    # next time (seconds) to spawn a rise
        self._sparkle_dust = []       # tiny sparkles falling from comet trail
        self._rise_count = 0          # total comets spawned
        self._next_color_change = int(np.random.uniform(3, 5))  # change color every 3-4
        self._current_comet_color = np.array([255, 140, 20], dtype=np.float32)
        self._current_comet_core  = np.array([255, 230, 180], dtype=np.float32)
        self._star_particles = []    # list of star particle dicts
        self._star_frame = 0         # frame counter for twinkling phase
        self._trail_glow_points = []  # lingering glow points from comet trails
        self._comet_trail_glow_enabled = False


__all__ = ["VisualEffects"]
