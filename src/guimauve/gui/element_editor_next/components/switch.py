"""On / off switch."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget

from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager

_KNOB_MARGIN = 2
_FOCUS_GAP = 2


class Switch(QAbstractButton):
    """Switch drawn with the theme colors; use clicked for changes made by the user, toggled for all of them."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self.setCheckable(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        theme.changed.connect(self.update)

    def sizeHint(self) -> QSize:
        margin = 2 * _FOCUS_GAP
        return QSize(METRICS.switch_width + margin, METRICS.switch_height + margin)

    def paintEvent(self, event: QPaintEvent) -> None:
        palette = self._theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.5)

        track = QRectF(0, 0, METRICS.switch_width, METRICS.switch_height)
        track.moveCenter(QRectF(self.rect()).center())
        radius = track.height() / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette.accent_fill if self.isChecked() else palette.switch_track))
        painter.drawRoundedRect(track, radius, radius)

        size = track.height() - 2 * _KNOB_MARGIN
        left = track.right() - _KNOB_MARGIN - size if self.isChecked() else track.left() + _KNOB_MARGIN
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(left, track.top() + _KNOB_MARGIN, size, size))

        if self.hasFocus():
            ring = track.adjusted(-_FOCUS_GAP, -_FOCUS_GAP, _FOCUS_GAP, _FOCUS_GAP)
            painter.setPen(QPen(QColor(palette.text_muted), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(ring, ring.height() / 2, ring.height() / 2)
