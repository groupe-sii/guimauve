"""Lucide icons embedded in the package, recolored and rendered at the size they are drawn."""

import tempfile
from enum import StrEnum
from functools import cache
from pathlib import Path

from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"
LOGO_FILE = Path(__file__).resolve().parent / "assets" / "logo" / "guimauve.svg"


class Icon(StrEnum):
    """Icons available, by Lucide file name; add a member with each new SVG."""

    ARROW_DOWN = "arrow-down"
    ARROW_UP = "arrow-up"
    BRACES = "braces"
    CAMERA = "camera"
    CHEVRON_DOWN = "chevron-down"
    CHEVRON_RIGHT = "chevron-right"
    CIRCLE_ALERT = "circle-alert"
    COPY = "copy"
    GRIP = "grip-vertical"
    IMAGE = "image"
    IMAGE_UP = "image-up"
    INFO = "info"
    MONITOR = "monitor"
    MOON = "moon"
    PANEL_LEFT_CLOSE = "panel-left-close"
    PANEL_LEFT_OPEN = "panel-left-open"
    PLUS = "plus"
    REDO = "redo-2"
    ROTATE_CCW = "rotate-ccw"
    SUN = "sun"
    TEXT_INPUT = "text-cursor-input"
    TIMER = "timer"
    TRASH = "trash-2"
    TRIANGLE_ALERT = "triangle-alert"
    TYPE = "type"
    UNDO = "undo-2"
    X = "x"


@cache
def icon(name: Icon, color: str, disabled_color: str) -> QIcon:
    """Returns the icon drawn in color, and in disabled_color when its widget is disabled."""
    svg = (ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8")
    return QIcon(_SvgEngine(svg.replace("currentColor", color), svg.replace("currentColor", disabled_color)))


@cache
def icon_file(name: Icon, color: str) -> Path:
    """Recolored copy of the SVG in the temporary folder, for the stylesheet, which only takes image files."""
    path = Path(tempfile.gettempdir()) / "guimauve-theme" / f"{name}-{color.lstrip('#')}.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((ICONS_DIR / f"{name}.svg").read_text(encoding="utf-8").replace("currentColor", color), "utf-8")
    return path


class _SvgEngine(QIconEngine):
    """Renders the SVG at the requested size and device pixel ratio, so the icon stays sharp on every screen."""

    def __init__(self, normal: str, disabled: str):
        super().__init__()
        self._sources = (normal, disabled)
        self._normal = QSvgRenderer(normal.encode())
        self._disabled = QSvgRenderer(disabled.encode())

    def paint(self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State) -> None:
        renderer = self._disabled if mode is QIcon.Mode.Disabled else self._normal
        renderer.render(painter, QRectF(rect))

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        return self.scaledPixmap(size, mode, state, 1.0)

    def scaledPixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State, scale: float) -> QPixmap:
        pixmap = QPixmap(size * scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, QRect(0, 0, pixmap.width(), pixmap.height()), mode, state)
        painter.end()
        pixmap.setDevicePixelRatio(scale)
        return pixmap

    def clone(self) -> QIconEngine:
        return _SvgEngine(*self._sources)


def logo() -> QIcon:
    """Logo of Guimauve, in its own colors whatever the theme: the icon of the window."""
    return QIcon(str(LOGO_FILE))
