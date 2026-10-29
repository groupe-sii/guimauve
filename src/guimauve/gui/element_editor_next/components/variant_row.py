"""Row of the variant list: number, type, thumbnail, name and badges; one column when the list is collapsed."""

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFocusEvent,
    QFont,
    QFontMetrics,
    QFontMetricsF,
    QImage,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from guimauve.gui.element_editor_next.components.badge import CenteredLabel, Dot
from guimauve.gui.element_editor_next.components.icon_label import IconLabel
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.state import VariantSummary
from guimauve.gui.element_editor_next.theme import METRICS, TYPE, Icon, ThemeManager

DIMMED_OPACITY = 0.45
FOUND = "Found by the last test"


class VariantKind(Enum):
    """Kind of a variant, shown by its icon; other kinds can come with new icons."""

    IMAGE = Icon.IMAGE
    TEXT = Icon.TYPE


MISSING_ICONS = {VariantKind.IMAGE: Icon.IMAGE, VariantKind.TEXT: Icon.TEXT_INPUT}
"""Icon in the dashed frame of a variant without its image or text."""


@dataclass(frozen=True)
class RowContent:
    """What a row shows.

    :param number: Position in the list, from 1.
    :param name: Name of the variant.
    :param kind: Kind of the variant.
    :param image: Thumbnail of an image variant; None without image.
    :param text: Text searched by a text variant.
    :param summary: Overrides and issues, shown as badges.
    :param dimmed: Faded, when the variants are not used.
    :param found: Found by the last test still valid: its match is the one a run would use.
    """

    number: int
    name: str
    kind: VariantKind
    image: QImage | None = None
    text: str = ""
    summary: VariantSummary = VariantSummary()
    dimmed: bool = False
    found: bool = False


class Thumbnail(QWidget):
    """Neutral frame with the image fitted inside, the beginning of a text, or a dashed frame with an icon."""

    def __init__(self, size: QSize, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self._image: QImage | None = None
        self._text = ""
        self._missing = Icon.IMAGE
        self.setFixedSize(size)
        theme.changed.connect(self.update)

    @staticmethod
    def box(size: QSize) -> QSize:
        """Size the image fits in, inside the padding of a frame of this size."""
        return size - QSize(METRICS.space(2), METRICS.space(2))

    def set_content(self, image: QImage | None, text: str = "", missing: Icon = Icon.IMAGE) -> None:
        """Shows the image, else the text, else the missing icon in a dashed frame."""
        self._image, self._text, self._missing = image, text, missing
        self.update()

    def is_missing(self) -> bool:
        return self._image is None and not self._text

    def missing_icon(self) -> Icon:
        return self._missing

    def paintEvent(self, event: QPaintEvent) -> None:
        palette = self._theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = METRICS.radius_control

        if self.is_missing():
            pen = QPen(QColor(palette.border_strong), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRoundedRect(frame.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
            size = METRICS.icon - 2
            icon = self._theme.icon(self._missing, "text_muted")
            icon.paint(painter, (self.width() - size) // 2, (self.height() - size) // 2, size, size)
            return

        painter.setPen(QPen(QColor(palette.border), 1))
        painter.setBrush(QColor(palette.surface_raised))
        painter.drawRoundedRect(frame, radius, radius)
        clip = QPainterPath()
        clip.addRoundedRect(frame, radius, radius)
        painter.setClipPath(clip)

        if self._image is not None:
            ratio = self._image.devicePixelRatio()
            width, height = self._image.width() / ratio, self._image.height() / ratio
            target = QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)
            painter.drawImage(target, self._image)
            return

        font = self.font()
        font.setPixelSize(TYPE.caption)
        font.setWeight(QFont.Weight(TYPE.bold))
        painter.setFont(font)
        painter.setPen(QColor(palette.text_secondary))
        inner = self.rect().adjusted(METRICS.space(1), 0, -METRICS.space(1), 0)
        text = QFontMetrics(font).elidedText(self._text, Qt.TextElideMode.ElideRight, inner.width())
        painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, text)


class ElidedLabel(CenteredLabel):
    """CenteredLabel that ends with an ellipsis when its text does not fit; the tooltip gives the full text."""

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, event: QPaintEvent) -> None:
        metrics = QFontMetricsF(self.font())
        rect = self.contentsRect()
        text = metrics.elidedText(self.text(), Qt.TextElideMode.ElideRight, rect.width())
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(QPointF(rect.x(), rect.y() + (rect.height() + metrics.capHeight()) / 2), text)


class VariantRow(QFrame):
    """One variant of the list; it shows a RowContent and never talks to the store.

    Badges are icons only, with their detail in the tooltip: errors, warnings, and the violet dot of the overrides.
    The grip on the left is where a drag starts. Collapsed, the row is one column with the number, the thumbnail
    and a dot for the most important badge, without grip.

    :param collapsed: One column, for the collapsed list.
    """

    renamed = Signal(str)
    """The user typed a new name, not empty and different from the current one."""

    def __init__(self, theme: ThemeManager, collapsed: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("variantRow", True)
        self.setProperty("selected", False)
        self._collapsed = collapsed
        self._content: RowContent | None = None

        self._number = CenteredLabel()
        self._number.setProperty("rowNumber", True)
        self._number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if collapsed:
            size = QSize(METRICS.thumbnail_small_width, METRICS.thumbnail_small_height)
        else:
            size = QSize(METRICS.thumbnail_width, METRICS.thumbnail_height)
        self.thumbnail = Thumbnail(size, theme)

        if collapsed:
            self._status = Dot(theme, size=METRICS.status_dot, parent=self)
            column = QVBoxLayout(self)
            column.setContentsMargins(0, METRICS.space(1) + 2, 0, METRICS.space(1) + 2)
            column.setSpacing(METRICS.space(1))
            column.addWidget(self._number, 0, Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(self.thumbnail, 0, Qt.AlignmentFlag.AlignHCenter)
            return

        self.grip = IconLabel(Icon.GRIP, theme, "text_muted")
        self.grip.setObjectName("grip")
        self.grip.setToolTip("Drag to reorder")
        self.grip.setCursor(Qt.CursorShape.OpenHandCursor)
        self._kind = IconLabel(Icon.IMAGE, theme)
        self._name = ElidedLabel()
        self._name.setProperty("variantName", True)
        self._name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._editor = QLineEdit()
        self._editor.setObjectName("rename")
        self._editor.hide()
        self._editor.installEventFilter(self)
        self._errors = IconLabel(Icon.CIRCLE_ALERT, theme, "error")
        self._warnings = IconLabel(Icon.TRIANGLE_ALERT, theme, "warning")
        self._overrides = Dot(theme, size=METRICS.status_dot)
        self._found = Dot(theme, "success", size=METRICS.status_dot)
        self._found.setObjectName("found")
        self._found.setToolTip(FOUND)
        self._found.hide()

        self._number.setFixedWidth(METRICS.space(3))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(1), METRICS.space(2), METRICS.space(2), METRICS.space(2))
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(self.grip)
        layout.addSpacing(-METRICS.space(1))  # the grip stays close to the number it moves
        layout.addWidget(self._number)
        layout.addWidget(self._kind)
        layout.addWidget(self.thumbnail)
        layout.addWidget(self._name, 1)
        layout.addWidget(self._editor, 1)
        for badge in (self._errors, self._warnings, self._overrides, self._found):
            layout.addWidget(badge)

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def set_content(self, content: RowContent) -> None:
        self._content = content
        self._number.setText(str(content.number))
        text = content.text if content.kind is VariantKind.TEXT else ""
        self.thumbnail.set_content(content.image, text, MISSING_ICONS[content.kind])
        summary = content.summary
        details = [*summary.errors, *summary.warnings]
        if summary.overrides:
            details.append(_overrides(summary.overrides))

        if self._collapsed:
            self._status.setVisible(bool(details) or content.found)
            role = "error" if summary.errors else "warning" if summary.warnings else "inherit"
            self._status.set_role(role if details else "success")
            self.setToolTip("\n".join([content.name, *details, *([FOUND] if content.found else [])]))
        else:
            self._kind.set_icon(content.kind.value)
            self._kind.setToolTip("Image" if content.kind is VariantKind.IMAGE else "Text")
            self._name.setText(content.name)
            self._name.setToolTip(content.name)
            self._errors.setVisible(bool(summary.errors))
            self._errors.setToolTip("\n".join(summary.errors))
            self._warnings.setVisible(bool(summary.warnings))
            self._warnings.setToolTip("\n".join(summary.warnings))
            self._overrides.setVisible(summary.overrides > 0)
            self._overrides.setToolTip(_overrides(summary.overrides))
            self._found.setVisible(content.found)

        self._set_dimmed(content.dimmed)

    def content(self) -> RowContent | None:
        return self._content

    def set_selected(self, selected: bool) -> None:
        set_style_property(self, "selected", selected)

    def is_renaming(self) -> bool:
        return not self._collapsed and not self._editor.isHidden()

    def start_rename(self) -> None:
        """Replaces the name by a field, with the name selected; Enter or leaving the field keeps it, Esc not."""
        if self._collapsed or self._content is None:
            return
        self._editor.setText(self._content.name)
        self._editor.selectAll()
        self._name.hide()
        self._editor.show()
        self._editor.setFocus()

    def eventFilter(self, watched, event) -> bool:  # type: ignore[no-untyped-def]  # QObject, QEvent
        if watched is self._editor and self.is_renaming():
            if isinstance(event, QKeyEvent) and event.type() == QKeyEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._finish_rename(keep=True)
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self._finish_rename(keep=False)
                    return True
            elif isinstance(event, QFocusEvent) and event.type() == QFocusEvent.Type.FocusOut:
                self._finish_rename(keep=True)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]  # QResizeEvent
        super().resizeEvent(event)
        if self._collapsed:  # the status dot sits on the top right corner of the thumbnail
            frame = self.thumbnail.geometry()
            self._status.move(frame.right() - METRICS.status_dot // 2, frame.top() - METRICS.status_dot // 2)
            self._status.raise_()

    def _finish_rename(self, keep: bool) -> None:
        name = self._editor.text().strip()
        self._editor.hide()
        self._name.show()
        if keep and self._content is not None and name and name != self._content.name:
            self.renamed.emit(name)

    def _set_dimmed(self, dimmed: bool) -> None:
        if dimmed == self.is_dimmed():
            return
        if dimmed:
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(DIMMED_OPACITY)
            self.setGraphicsEffect(effect)
        else:
            self.setGraphicsEffect(None)  # type: ignore[arg-type]  # None removes the effect

    def is_dimmed(self) -> bool:
        return self.graphicsEffect() is not None


def _overrides(count: int) -> str:
    return f"{count} override{'' if count == 1 else 's'}"
