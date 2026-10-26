"""Spinner from the logo, « Hop »: the two marshmallows bounce in turn, squashing on landing."""

from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QHideEvent, QPainter, QPaintEvent, QShowEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from guimauve.gui.element_editor_next.theme import BRAND

CYCLE_MS = 1200
BOX = QRectF(5, 16, 90, 66)
"""Part of the 100 px drawing of the mockup the spinner covers: both marshmallows squashed and at the top of a hop."""
SIDE, RADIUS = 40.0, 15.0
GROUND = 82.0
"""Bottom of the marshmallows at rest, in the drawing."""
LEFTS = (8.0, 52.0)
HOP = 22.0


@dataclass(frozen=True)
class Pose:
    """Lift of a marshmallow above the ground, and its scale around the middle of its bottom."""

    lift: float = 0.0
    width: float = 1.0
    height: float = 1.0


ROSE_KEYS = (
    (0.0, Pose()),
    (0.1, Pose(0, 1.12, 0.86)),
    (0.3, Pose(HOP, 0.94, 1.08)),
    (0.5, Pose(0, 1.1, 0.9)),
    (0.6, Pose()),
    (1.0, Pose()),
)
VIOLET_KEYS = (
    (0.0, Pose()),
    (0.4, Pose()),
    (0.5, Pose(0, 1.12, 0.86)),
    (0.7, Pose(HOP, 0.94, 1.08)),
    (0.9, Pose(0, 1.1, 0.9)),
    (1.0, Pose()),
)
"""Keyframes of the mockup, the violet one half a cycle after the rose one."""
_EASE = QEasingCurve(QEasingCurve.Type.InOutSine)


def pose_at(progress: float, keys: tuple[tuple[float, Pose], ...]) -> Pose:
    """Pose at a point of the cycle, from 0 to 1, eased between the keyframes as CSS ease-in-out does."""
    progress %= 1.0
    for (start, before), (end, after) in zip(keys, keys[1:], strict=False):
        if start <= progress <= end:
            ratio = 0.0 if end == start else _EASE.valueForProgress((progress - start) / (end - start))
            return Pose(
                before.lift + (after.lift - before.lift) * ratio,
                before.width + (after.width - before.width) * ratio,
                before.height + (after.height - before.height) * ratio,
            )
    return keys[-1][1]


class Spinner(QWidget):
    """Two marshmallows in the colors of the brand, wider than tall; runs while shown.

    :param height: Height of the spinner, e.g. 14 beside a short text; its width follows.
    """

    def __init__(self, height: int = 14, parent: QWidget | None = None):
        super().__init__(parent)
        self._size = QSize(round(height * BOX.width() / BOX.height()), height)
        self.setFixedSize(self._size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._progress = 0.0
        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(CYCLE_MS)
        self._animation.setLoopCount(-1)
        self._animation.valueChanged.connect(self._advance)

    def sizeHint(self) -> QSize:
        return self._size

    def is_running(self) -> bool:
        return self._animation.state() == QVariantAnimation.State.Running

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._animation.start()

    def hideEvent(self, event: QHideEvent) -> None:
        self._animation.stop()
        super().hideEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = self.height() / BOX.height()
        painter.scale(scale, scale)
        painter.translate(-BOX.left(), -BOX.top())
        painter.setPen(Qt.PenStyle.NoPen)
        for left, color, keys in ((LEFTS[0], BRAND.rose, ROSE_KEYS), (LEFTS[1], BRAND.violet, VIOLET_KEYS)):
            pose = pose_at(self._progress, keys)
            width, height = SIDE * pose.width, SIDE * pose.height
            bottom = QPointF(left + SIDE / 2, GROUND - pose.lift)
            painter.setBrush(QColor(color))
            rect = QRectF(bottom.x() - width / 2, bottom.y() - height, width, height)
            painter.drawRoundedRect(rect, RADIUS * pose.width, RADIUS * pose.height)
        painter.end()

    def _advance(self, value: float) -> None:
        self._progress = value
        self.update()
