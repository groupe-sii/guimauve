"""Small markers: the badges of a section header and the violet dot of an overridden value."""

from enum import StrEnum

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QFontMetricsF, QPainter, QPaintEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QStyle, QStyleOption, QWidget

from guimauve.gui.element_editor_next.components.icon_label import IconLabel
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager


class CenteredLabel(QLabel):
    """Single line of text centered vertically on the height of its capitals and digits, not on its line box.

    QLabel centers the line box, ascent and descent included, which leaves text a fraction of a pixel off the
    icons and badges beside it, by an amount that changes with the font and the font engine. Horizontally, the
    text follows the alignment of the label. The background still comes from the stylesheet.
    """

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        option = QStyleOption()
        option.initFrom(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)
        metrics = QFontMetricsF(self.font())
        rect = self.contentsRect()
        width = metrics.horizontalAdvance(self.text())
        horizontal = self.alignment() & Qt.AlignmentFlag.AlignHorizontal_Mask
        if horizontal & Qt.AlignmentFlag.AlignRight:
            x = rect.right() + 1 - width
        elif horizontal & Qt.AlignmentFlag.AlignHCenter:
            x = rect.x() + (rect.width() - width) / 2
        else:
            x = rect.x()
        baseline = rect.y() + (rect.height() + metrics.capHeight()) / 2
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(QPointF(x, baseline), self.text())


class Badge(CenteredLabel):
    """Violet pill with a short text, such as the number of values set in a section."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setProperty("badge", "inherit")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(METRICS.badge_height)
        self.setMinimumWidth(METRICS.badge_height)


class Count(StrEnum):
    """What a CountBadge counts, read by the stylesheet."""

    CODE = "code"
    ERROR = "error"
    WARNING = "warning"


class CountBadge(QFrame):
    """Icon and number, so the color is never the only cue: values set in the code, errors or warnings.

    Hidden at 0.
    """

    _ICONS = {
        Count.CODE: (Icon.BRACES, "inherit"),
        Count.ERROR: (Icon.CIRCLE_X, "error"),
        Count.WARNING: (Icon.TRIANGLE_ALERT, "warning"),
    }

    def __init__(self, kind: Count, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("badge", kind.value)
        self.setFixedHeight(METRICS.badge_height)
        name, role = self._ICONS[kind]
        self._count = CenteredLabel()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(1), 0, METRICS.space(2), 0)
        layout.setSpacing(METRICS.space(1))
        layout.addWidget(IconLabel(name, theme, role, size=METRICS.badge_height - 4))
        layout.addWidget(self._count)

    def set_count(self, count: int) -> None:
        self._count.setText(str(count))
        self.setVisible(count > 0)

    def count(self) -> int:
        return int(self._count.text() or 0)


class Dot(QWidget):
    """Violet dot of a value set on the element or the variant.

    :param role: Color of the palette, by role name, e.g. "error" for the status dot of a collapsed variant.
    :param size: Diameter in pixels.
    """

    def __init__(
        self, theme: ThemeManager, role: str = "inherit", size: int = METRICS.dot, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self._theme = theme
        self._role = role
        self.setFixedSize(QSize(size, size))
        theme.changed.connect(self.update)

    def set_role(self, role: str) -> None:
        self._role = role
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(getattr(self._theme.palette, self._role)))
        painter.drawEllipse(self.rect())
