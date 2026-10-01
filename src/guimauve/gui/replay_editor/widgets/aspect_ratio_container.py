"""A container widget that keeps its child at a fixed aspect ratio."""

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent, QShowEvent
from PySide6.QtWidgets import QWidget


class AspectRatioContainer(QWidget):
    """Centers ``child_widget`` inside itself, sized to respect ``ratio``.

    Unlike Qt's ``heightForWidth`` mechanism (unreliable inside layouts
    and prone to feedback loops), this widget positions its child
    directly with ``setGeometry()``. It never asks its parent layout
    for more space than it was given, so it cannot trigger the
    grow-forever bug that ``setFixedWidth()``/``setFixedHeight()`` caused.

    :ivar child: The wrapped widget.
    :vartype child: QWidget
    :ivar ratio: Locked aspect ratio, expressed as ``height / width``.
    :vartype ratio: float
    """

    def __init__(
        self,
        child_widget: QWidget,
        ratio: float,
        parent: QWidget | None = None,
    ) -> None:
        """
        :param child_widget: The widget to keep at a fixed aspect ratio.
        :param ratio: Locked aspect ratio, expressed as ``height / width``
            (e.g. ``9/16`` for a 16:9 widget).
        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self.child = child_widget
        self.ratio = ratio
        self.child.setParent(self)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        """Recompute the child geometry to keep the ratio locked.

        :param event: The Qt resize event, or ``None`` when called
            manually from :meth:`showEvent`.
        """
        if event is not None:
            super().resizeEvent(event)

        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return

        target_height = width * self.ratio
        if target_height <= height:
            new_width, new_height = width, target_height
        else:
            new_width, new_height = height / self.ratio, height

        x = (width - new_width) / 2
        y = (height - new_height) / 2
        self.child.setGeometry(int(x), int(y), int(new_width), int(new_height))

    def showEvent(self, event: QShowEvent) -> None:
        """Force one layout pass before the first paint.

        ``resizeEvent`` is not guaranteed to fire before the first
        paint, so we invoke it manually when the widget appears.

        :param event: The Qt show event.
        """
        super().showEvent(event)
        self.resizeEvent(None)

    def sizeHint(self) -> QSize:
        """:return: The preferred size, identical to the minimum size hint."""
        return self.minimumSizeHint()

    def minimumSizeHint(self) -> QSize:
        """Give the parent layout something non-zero to allocate.

        Without this the container may collapse to ``0x0`` and
        :meth:`resizeEvent` never gets a chance to run.

        :return: A 200-unit-wide box respecting the container's ratio.
        """
        width = 200
        return QSize(width, int(width * self.ratio))
