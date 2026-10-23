"""Centre of the window: the image of the selected variant, with the bars above and under it."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.canvas import CanvasStatusBar, CanvasTopBar, CanvasView
from guimauve.gui.element_editor_next.canvas.top_bar import ACTUAL_SIZE, FIT, ZOOM_IN, ZOOM_IN_EXTRA, ZOOM_OUT
from guimauve.gui.element_editor_next.components import IconLabel
from guimauve.gui.element_editor_next.services.images import to_qimage
from guimauve.gui.element_editor_next.state import Store
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager
from guimauve.models.variant import ImageVariant

EMPTY_TITLE = "No image for this variant"
EMPTY_HINT = "Use Capture in the toolbar to take one."
EMPTY_ICON = 28
EMPTY_WIDTH = 360


class CanvasPanel(QFrame):
    """Image of the selected variant, fitted again whenever another variant is selected or its image changes.

    An image variant without image shows how to capture one; a text variant or no selection shows the background
    only, until the text variants have their own view. The zoom shortcuts work in the whole window.
    """

    def __init__(self, store: Store, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("canvas")
        self._store = store
        self._variant: int | None = None
        self._array: np.ndarray | None = None  # image shown, compared by identity: a new image is a new array

        self.top_bar = CanvasTopBar(theme)
        self.view = CanvasView(theme)
        self.status_bar = CanvasStatusBar()
        self.empty = _empty_card(theme)
        overlay = QGridLayout(self.view.viewport())
        overlay.setContentsMargins(*[METRICS.canvas_margin] * 4)
        overlay.addWidget(self.empty, 0, 0, Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.top_bar)
        layout.addWidget(self.view, 1)
        layout.addWidget(self.status_bar)

        self.top_bar.zoom_in_requested.connect(self.view.zoom_in)
        self.top_bar.zoom_out_requested.connect(self.view.zoom_out)
        self.top_bar.fit_requested.connect(self.view.fit)
        self.top_bar.zoom_requested.connect(self.view.set_zoom)
        self.view.zoom_changed.connect(self._show_zoom)
        self.view.hovered_changed.connect(self._show_pixel)
        for keys, slot in (
            (FIT, self.view.fit),
            (ACTUAL_SIZE, lambda: self.view.set_zoom(1.0)),
            (ZOOM_IN, self.view.zoom_in),
            (ZOOM_IN_EXTRA, self.view.zoom_in),
            (ZOOM_OUT, self.view.zoom_out),
        ):
            QShortcut(QKeySequence(keys), self, slot)

        store.selection_changed.connect(self._refresh)
        store.document_changed.connect(self._refresh)
        self._refresh(force=True)

    def _refresh(self, force: bool = False) -> None:
        key = self._store.selected_variant
        variant = None if key is None else self._store.document.get(key)
        array = variant.image if isinstance(variant, ImageVariant) else None
        if not force and key == self._variant and array is self._array:
            return
        self._variant, self._array = key, array
        self.empty.setVisible(isinstance(variant, ImageVariant) and array is None)
        self.view.set_image(None if array is None else to_qimage(array))
        self._show_zoom()
        self._show_pixel()

    def _show_zoom(self) -> None:
        self.top_bar.show_zoom(None if self.view.image() is None else self.view.zoom)

    def _show_pixel(self) -> None:
        image = self.view.image()
        size = None if image is None else (image.width(), image.height())
        self.status_bar.show_pixel(size, self.view.hovered_pixel(), self.view.hovered_color())


def _empty_card(theme: ThemeManager) -> QFrame:
    card = QFrame()
    card.setProperty("emptyCard", True)
    card.setFixedWidth(EMPTY_WIDTH)
    title = QLabel(EMPTY_TITLE)
    title.setProperty("emptyTitle", True)
    hint = QLabel(EMPTY_HINT)
    hint.setProperty("muted", True)
    layout = QVBoxLayout(card)
    margin = METRICS.space(8)
    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(METRICS.space(2))
    for widget in (IconLabel(Icon.IMAGE, theme, "text_muted", EMPTY_ICON), title, hint):
        layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignHCenter)
    return card
