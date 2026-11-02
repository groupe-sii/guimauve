"""Zoom of the canvas, as physical pixels of the screen per pixel of the image; without Qt.

At 100 %, the image looks the same size as on the screen it was captured from, whatever the scaling of the system.
"""

MIN_ZOOM = 0.05
MAX_ZOOM = 32.0
FIT_MAX = 2.0
"""A small image fits the canvas enlarged at most twice, so it does not look blurred."""
WHEEL_STEP = 1.2
"""Factor of one notch of the wheel."""
PRESETS = (0.5, 1.0, 2.0, 4.0)
"""Levels offered in the zoom menu, besides fitting the window."""
LEVELS = (0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0)
"""Levels reached by the zoom in and zoom out buttons."""


def clamp(zoom: float) -> float:
    return min(max(zoom, MIN_ZOOM), MAX_ZOOM)


def fit(width: int, height: int, view_width: float, view_height: float) -> float:
    """Zoom showing a whole image in a view, both in physical pixels, enlarged at most FIT_MAX times."""
    if width <= 0 or height <= 0 or view_width <= 0 or view_height <= 0:
        return 1.0
    return clamp(min(view_width / width, view_height / height, FIT_MAX))


def wheel(zoom: float, notches: float) -> float:
    """Zoom after turning the wheel, by notches forward (in) or backward (out)."""
    return clamp(zoom * WHEEL_STEP**notches)


def zoom_in(zoom: float) -> float:
    """Next level above the zoom."""
    return next((level for level in LEVELS if level > zoom * 1.001), MAX_ZOOM)


def zoom_out(zoom: float) -> float:
    """Next level below the zoom."""
    return next((level for level in reversed(LEVELS) if level < zoom / 1.001), MIN_ZOOM)


def label(zoom: float) -> str:
    """Zoom as shown, e.g. "150 %"."""
    return f"{round(zoom * 100)} %"
