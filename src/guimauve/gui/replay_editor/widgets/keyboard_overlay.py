"""Semi-transparent overlay showing currently pressed keys on the canvas.

Presentation only: takes a list of key names and an opacity, and paints
them at the bottom-center of its parent widget.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from guimauve.gui.replay_editor.constants import KEY_DISPLAY


class KeyboardOverlay(QLabel):
    """A QLabel anchored to the bottom-center of its parent, with fade."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        :param parent: The widget the overlay anchors to. Should be
            provided in practice — the overlay only shows itself when
            it has a parent to attach to.
        """
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel {
                background: rgba(20, 20, 20, 200);
                color: white;
                font-size: 22px;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 10px;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        self.hide()

    def show_keys(self, keys: list[str] | None, opacity: float = 1.0) -> None:
        """Display ``keys`` at ``opacity``, or hide the overlay if empty.

        :param keys: Key names to display, in the order they should
            appear. Names are looked up in :data:`KEY_DISPLAY` and
            replaced by their symbol; unknown names are shown as-is.
            ``None`` or an empty list hides the overlay.
        :param opacity: Fade factor in ``[0, 1]``. A value of ``0`` or
            less hides the overlay.
        """
        if not keys or opacity <= 0:
            self.hide()
            return

        self.setText(self._format_keys(keys))
        self._opacity_effect.setOpacity(opacity)
        self.adjustSize()
        self.reposition()
        self.show()

    def reposition(self) -> None:
        """Re-anchor the overlay to the bottom-center of its parent.

        Called automatically on every :meth:`show_keys`; call it
        externally after the parent widget resizes.
        """
        parent = self.parent()
        if not isinstance(parent, QWidget):
            return
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - 20
        self.move(x, y)

    @staticmethod
    def _format_keys(keys: list[str]) -> str:
        """Join key names into a display string, substituting symbols.

        :param keys: The key names to format.
        :return: A space-separated string of display symbols.
        """
        return " ".join(KEY_DISPLAY.get(k, k) for k in keys)
