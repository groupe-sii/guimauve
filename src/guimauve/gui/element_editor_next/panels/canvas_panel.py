"""Centre of the window: the image of the selected variant, with the bars above and under it."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.canvas import (
    HELP,
    CanvasStatusBar,
    CanvasTopBar,
    CanvasView,
    EditToolbar,
    TargetMarker,
)
from guimauve.gui.element_editor_next.canvas.top_bar import ACTUAL_SIZE, FIT, ZOOM_IN, ZOOM_IN_EXTRA, ZOOM_OUT
from guimauve.gui.element_editor_next.components import IconLabel
from guimauve.gui.element_editor_next.services.images import to_qimage
from guimauve.gui.element_editor_next.state import Store, resolve
from guimauve.gui.element_editor_next.state.geometry import is_inside, whole
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

    The targets of the variant are selected, dragged, nudged and deleted on the image; a drag is one undo step.
    The floating bar chooses the tool; in the Target tool, a click adds a target and selects it.
    """

    def __init__(self, store: Store, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("canvas")
        self._store = store
        self._variant: int | None = None
        self._array: np.ndarray | None = None  # image shown, compared by identity: a new image is a new array
        self._gesture: int | None = None  # drag of a target in progress

        self.top_bar = CanvasTopBar(theme)
        self.view = CanvasView(theme)
        self.status_bar = CanvasStatusBar()
        self.empty = _empty_card(theme)
        overlay = QGridLayout(self.view.viewport())
        overlay.setContentsMargins(*[METRICS.canvas_margin] * 4)
        overlay.addWidget(self.empty, 0, 0, Qt.AlignmentFlag.AlignCenter)
        self.tools = EditToolbar(theme, self.view.viewport())
        self.tools.move(METRICS.space(3), METRICS.space(3))

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
        self.view.target_pressed.connect(self._press_target)
        self.view.target_dragged.connect(self._drag_target)
        self.view.target_released.connect(self._release_target)
        self.view.background_clicked.connect(lambda: store.select(store.selected_variant))
        self.view.nudge_requested.connect(self._nudge_target)
        self.view.delete_requested.connect(self._delete_target)
        self.view.target_added.connect(self._add_target)
        self.view.tool_changed.connect(self._show_tool)
        self.tools.tool_chosen.connect(self.view.set_tool)
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
        store.mode_changed.connect(self._refresh)  # trials may change the target used
        self._refresh(force=True)
        self._show_tool()

    def _refresh(self, force: bool = False) -> None:
        key = self._store.selected_variant
        variant = None if key is None else self._store.document.get(key)
        array = variant.image if isinstance(variant, ImageVariant) else None
        if force or key != self._variant or array is not self._array:
            self._variant, self._array = key, array
            self.empty.setVisible(isinstance(variant, ImageVariant) and array is None)
            self.tools.setVisible(array is not None)
            self.view.set_image(None if array is None else to_qimage(array))
            self._show_zoom()
            self._show_pixel()
        self.view.set_targets(self._markers(variant) if isinstance(variant, ImageVariant) else [])

    def _markers(self, variant: ImageVariant) -> list[TargetMarker]:
        if variant.image is None:
            return []
        store = self._store
        height, width = variant.image.shape[:2]
        image = whole(width, height)
        spec = resolve("target", store.document, store.default, variant, include_code=store.include_code).value
        # As the detection resolves it: a name, or else the default target, picks the first target of that name, the
        # first unnamed target with neither; coordinates or a name not found pick none.
        name = spec if isinstance(spec, str) else variant.default_target
        targets = [] if isinstance(spec, (tuple, list)) else variant.targets or []
        used = next((target for target in targets if target.name == name), None)
        return [
            TargetMarker(
                key=(target_key := store.document.key(target)),
                number=number,
                name=target.name,
                x=target.x,
                y=target.y,
                used=target is used,
                selected=target_key == store.selected_target,
                outside=not is_inside(target, image),
            )
            for number, target in enumerate(variant.targets or [], start=1)
        ]

    # Tools

    def _show_tool(self) -> None:
        tool = self.view.tool
        self.tools.show_tool(tool)
        self.top_bar.show_help(HELP.get(tool))

    # Targets

    def _add_target(self, x: int, y: int) -> None:
        if self._variant is not None and self._array is not None:
            self._store.add_target(self._variant, x, y)

    def _press_target(self, target: int) -> None:
        self._store.select(self._store.selected_variant, target)
        self._gesture = self._store.new_gesture()

    def _drag_target(self, target: int, x: int, y: int) -> None:
        self._store.move_target(target, x, y, self._gesture)

    def _release_target(self, target: int) -> None:
        self._gesture = None

    def _nudge_target(self, dx: int, dy: int) -> None:
        if self._store.selected_target is not None:
            self._store.nudge_target(self._store.selected_target, dx, dy)

    def _delete_target(self) -> None:
        store = self._store
        if store.selected_variant is not None and store.selected_target is not None:
            store.remove_target(store.selected_variant, store.selected_target)

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
