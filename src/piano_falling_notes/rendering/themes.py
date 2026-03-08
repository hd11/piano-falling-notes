"""Theme presets and auto-selection based on music analysis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    label: str  # display name
    background_color: tuple[int, int, int]
    palette: tuple[tuple[int, int, int], ...]  # 12 chromatic colors C..B


THEMES: dict[str, Theme] = {
    "classic": Theme(
        name="classic",
        label="Classic",
        background_color=(15, 15, 20),
        palette=(
            (255, 50, 50), (255, 120, 30), (255, 190, 0), (230, 255, 0),
            (80, 255, 80), (0, 230, 160), (0, 200, 255), (30, 120, 255),
            (100, 60, 255), (180, 40, 255), (255, 50, 200), (255, 60, 120),
        ),
    ),
    "midnight": Theme(
        name="midnight",
        label="Midnight",
        background_color=(8, 8, 24),
        palette=(
            (100, 120, 255), (80, 160, 255), (60, 200, 255), (80, 220, 230),
            (100, 180, 255), (120, 140, 255), (140, 100, 255), (160, 80, 255),
            (180, 100, 255), (200, 120, 255), (160, 140, 255), (120, 160, 255),
        ),
    ),
    "sunset": Theme(
        name="sunset",
        label="Sunset",
        background_color=(25, 12, 15),
        palette=(
            (255, 80, 40), (255, 120, 50), (255, 160, 40), (255, 200, 60),
            (255, 220, 100), (255, 180, 80), (255, 140, 60), (255, 100, 70),
            (240, 80, 100), (220, 60, 130), (255, 90, 80), (255, 110, 60),
        ),
    ),
    "ocean": Theme(
        name="ocean",
        label="Ocean",
        background_color=(6, 16, 24),
        palette=(
            (0, 200, 180), (0, 220, 200), (20, 240, 220), (60, 230, 200),
            (0, 210, 255), (0, 180, 255), (30, 150, 255), (60, 120, 255),
            (80, 200, 230), (40, 230, 210), (0, 190, 240), (20, 210, 230),
        ),
    ),
    "neon": Theme(
        name="neon",
        label="Neon",
        background_color=(3, 3, 8),
        palette=(
            (255, 0, 60), (255, 80, 0), (255, 255, 0), (0, 255, 80),
            (0, 255, 200), (0, 255, 255), (0, 160, 255), (0, 80, 255),
            (130, 0, 255), (255, 0, 255), (255, 0, 160), (255, 60, 100),
        ),
    ),
    "pastel": Theme(
        name="pastel",
        label="Pastel",
        background_color=(18, 16, 22),
        palette=(
            (255, 150, 150), (255, 180, 140), (255, 210, 140), (240, 240, 160),
            (160, 240, 180), (150, 230, 210), (150, 210, 240), (160, 180, 240),
            (180, 160, 240), (210, 160, 240), (240, 160, 220), (255, 160, 190),
        ),
    ),
}

THEME_NAMES = list(THEMES.keys())


def auto_select_theme(metadata: dict) -> Theme:
    """Pick a theme based on key signature and tempo."""
    mode = metadata.get("key_mode", "major")
    tempo = metadata.get("tempo_bpm", 120.0)

    if tempo > 140:
        return THEMES["neon"]
    if tempo < 72:
        return THEMES["ocean"]
    if mode == "minor":
        return THEMES["midnight"]
    if mode == "major":
        return THEMES["sunset"]
    return THEMES["classic"]
