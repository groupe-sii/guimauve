"""One line of text cut with an ellipsis to fit its width."""

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLabel, QWidget


class ElidedLabel(QLabel):
    """Single line of text ending with an ellipsis when it does not fit; the whole text is its tooltip then.

    It asks for no width of its own, so a long text never widens its parent; its size hint is still the width of
    the whole text. text() is the text shown, full_text() the one set.
    """

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._full = ""
        self.setText(text)

    def setText(self, text: str) -> None:
        self._full = text
        self._elide()
        self.updateGeometry()

    def full_text(self) -> str:
        return self._full

    def sizeHint(self) -> QSize:
        margins = self.contentsMargins()
        width = self.fontMetrics().horizontalAdvance(self._full) + margins.left() + margins.right() + 2 * self.margin()
        return QSize(width, super().sizeHint().height())

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._elide()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.FontChange:  # e.g. the stylesheet applied
            self._elide()
            self.updateGeometry()

    def _elide(self) -> None:
        width = self.contentsRect().width() - 2 * self.margin()
        shown = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, width)
        super().setText(shown)
        self.setToolTip(self._full if shown != self._full else "")
