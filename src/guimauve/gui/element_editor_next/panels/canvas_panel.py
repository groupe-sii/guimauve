"""Centre of the window: the image of the selected variant, with the bars above and under it."""

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFrame, QGridLayout, QInputDialog, QLabel, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.canvas import (
    HELP,
    REGION_TOOLS,
    CanvasStatusBar,
    CanvasTopBar,
    CanvasView,
    EditToolbar,
    Region,
    RegionPanel,
    TargetMarker,
    Tool,
)
from guimauve.gui.element_editor_next.canvas.top_bar import ACTUAL_SIZE, FIT, ZOOM_IN, ZOOM_IN_EXTRA, ZOOM_OUT
from guimauve.gui.element_editor_next.components import IconLabel
from guimauve.gui.element_editor_next.panels.capture_flow import MAX_DELAY, CaptureFlow
from guimauve.gui.element_editor_next.panels.test_flow import TestFlow
from guimauve.gui.element_editor_next.panels.text_centre import TextCentre
from guimauve.gui.element_editor_next.services import CaptureSource
from guimauve.gui.element_editor_next.services.images import to_qimage
from guimauve.gui.element_editor_next.state import Mode, Store
from guimauve.gui.element_editor_next.state.geometry import intersect, is_inside, whole
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager
from guimauve.models.area import Area
from guimauve.models.variant import ImageVariant, TextVariant

EMPTY_TITLE = "No image for this variant"
EMPTY_HINT = "Use Capture in the toolbar to take one."
EMPTY_ICON = 28
EMPTY_WIDTH = 360


class CanvasPanel(QFrame):
    """Image of the selected variant, fitted again whenever another variant is selected or its image changes.

    An image variant without image shows how to capture one; a text variant shows the text it looks for, over the
    background, without the bar under the canvas, nor the focus of the view; no selection shows the background only.
    The zoom shortcuts work in the whole window.

    The targets of the variant are selected, dragged, nudged and deleted on the image; a drag is one undo step.
    The floating bar chooses the tool; in the Target tool, a click adds a target and selects it.

    The Match area tool, also opened from the Variant tab through the store, edits a rectangle starting from the
    match area; Apply or Enter sets it. The Crop tool starts from the whole image, warns of the targets the crop
    would leave outside, and crops on Crop or Enter. An edit closes, unapplied, when the variant, its image or the
    match area it edits changes.

    With a capture flow, the bar above offers to capture the image of an image variant, or to recapture it, and
    shows the capture errors.

    In Test mode the variant is shown read-only: no floating bar, no capture, no edit of the targets, and an edit
    in progress closes; the zoom and the panning stay. With a Test flow, the bar above then offers the capture to
    test on, the code overrides, the scope and Run test, shows a spinner while a test runs, and Esc cancels it.
    """

    def __init__(
        self,
        store: Store,
        theme: ThemeManager,
        capture: CaptureFlow | None = None,
        test: TestFlow | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("canvas")
        self.setMinimumWidth(METRICS.canvas_min_width)  # not the width of the texts of its bars, which depends on fonts
        self._store = store
        self._capture = capture
        self._variant: int | None = None
        self._array: np.ndarray | None = None  # image shown, compared by identity: a new image is a new array
        self._gesture: int | None = None  # drag of a target in progress
        self._edited: object = None  # value being edited by a rectangle tool, to close the edit if it changes

        self.top_bar = CanvasTopBar(theme)
        self.view = CanvasView(theme)
        self.status_bar = CanvasStatusBar()
        self.empty = _empty_card(theme)
        self.text_centre = TextCentre(store, theme)  # shows itself for a text variant only
        overlay = QGridLayout(self.view.viewport())
        overlay.setContentsMargins(*[METRICS.canvas_margin] * 4)
        overlay.addWidget(self.empty, 0, 0, Qt.AlignmentFlag.AlignCenter)
        overlay.addWidget(self.text_centre, 0, 0, Qt.AlignmentFlag.AlignCenter)
        self.tools = EditToolbar(theme, self.view.viewport())
        self.tools.move(METRICS.space(3), METRICS.space(3))
        self.region_panel = RegionPanel(theme, self.view.viewport())

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
        self.tools.hide_toggled.connect(self.view.set_overlays_hidden)
        self.view.overlays_changed.connect(lambda: self.tools.show_hidden(self.view.overlays_hidden()))
        self.view.region_changed.connect(self._place_region_panel)
        self.view.moved.connect(self._place_region_panel)
        self.view.region_confirmed.connect(self._apply_region)
        self.region_panel.applied.connect(self._apply_region)
        self.region_panel.cancelled.connect(lambda: self.view.set_tool(Tool.SELECT))
        store.match_area_edit_requested.connect(self._edit_match_area)
        if capture is not None:
            self.top_bar.capture_requested.connect(self._take_image)
            self.top_bar.delay_chosen.connect(self._capture_after)
            self.top_bar.custom_delay_requested.connect(self._ask_delay)
            capture.changed.connect(self._show_capture)
        self.top_bar.error_closed.connect(self._close_error)
        self._test = test
        self._cancel_test = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._cancel_test.setEnabled(False)
        if test is not None:
            source, controls = self.top_bar.test_source, self.top_bar.test_controls
            source.source_chosen.connect(test.capture)
            source.delay_chosen.connect(self._test_after)
            source.custom_delay_requested.connect(self._ask_test_delay)
            controls.code_toggled.connect(store.set_include_code)
            controls.scope_chosen.connect(store.set_test_scope)
            controls.run_requested.connect(store.request_test)
            self._cancel_test.activated.connect(test.cancel)
            test.changed.connect(self._show_test)
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
        store.mode_changed.connect(self._refresh)  # read-only in Test, where trials may change the target used
        self._refresh(force=True)
        self._show_tool()
        self._show_capture()
        self._show_test()

    def _refresh(self, force: bool = False) -> None:
        key = self._store.selected_variant
        variant = None if key is None else self._store.document.get(key)
        array = variant.image if isinstance(variant, ImageVariant) else None
        if force or key != self._variant or array is not self._array:
            self._variant, self._array = key, array
            self.empty.setVisible(isinstance(variant, ImageVariant) and array is None)
            text = isinstance(variant, TextVariant)
            self.status_bar.setVisible(not text)
            # The keys of the tools are not taken from the field; a click on the background leaves its focus alone.
            self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus if text else Qt.FocusPolicy.StrongFocus)
            if text and self.view.hasFocus():
                self.view.clearFocus()
            self._show_capture()
            self.view.set_image(None if array is None else to_qimage(array))
            self._show_zoom()
            self._show_pixel()
        testing = self._store.mode is Mode.TEST
        if force or testing != self.view.is_read_only():
            self.view.set_read_only(testing)
            self.setMinimumWidth(METRICS.canvas_test_min_width if testing else METRICS.canvas_min_width)
            self._show_capture()
            self._show_test()
        self.tools.setVisible(array is not None and not testing)
        self.view.set_targets(self._markers(variant) if isinstance(variant, ImageVariant) else [])
        area = variant.match_area if isinstance(variant, ImageVariant) else None
        self.view.set_match_area(None if area is None else Region.of(area))
        if self.view.tool is Tool.MATCH_AREA and area != self._edited:
            self.view.set_tool(Tool.SELECT)  # changed elsewhere, by an undo for instance
        self._place_region_panel()  # the targets left outside by a crop may have changed

    def _markers(self, variant: ImageVariant) -> list[TargetMarker]:
        if variant.image is None:
            return []
        store = self._store
        height, width = variant.image.shape[:2]
        image = whole(width, height)
        spec = store.resolve("target", store.document.key(variant)).value
        # As the detection resolves it: a name, or else the default target, picks the first target of that name, the
        # first unnamed target with neither; coordinates or a name not found pick none.
        name = spec if isinstance(spec, str) else variant.default_target
        targets = [] if isinstance(spec, (tuple, list)) else variant.targets or []
        used = next((target for target in targets if target.name == name), None)
        return [
            TargetMarker(
                key=(target_key := store.document.key(target)),
                number=number if len(variant.targets or []) > 1 else None,
                name=target.name,
                x=target.x,
                y=target.y,
                used=target is used,
                selected=target_key == store.selected_target,
                outside=not is_inside(target, image),
            )
            for number, target in enumerate(variant.targets or [], start=1)
        ]

    # Capture

    def _show_capture(self) -> None:
        flow = self._capture
        if flow is None:
            return
        variant = self._store.document.get(self._variant) if self._variant is not None else None
        image = isinstance(variant, ImageVariant)
        editing = self._store.mode is Mode.EDIT
        self.top_bar.set_capture(image and editing, image and self._array is not None, flow.delay, flow.initial_error)
        self.top_bar.set_remote(flow.is_remote)
        self.top_bar.capture_button.setEnabled(not flow.is_busy())
        if editing:  # the Test shows its own
            self.top_bar.show_capturing(flow.is_capturing())
            self.top_bar.show_error(flow.error)

    def _close_error(self) -> None:
        flow = self._capture if self._store.mode is Mode.EDIT else self._test
        if flow is not None:
            flow.clear_error()

    def _take_image(self, source: CaptureSource) -> None:
        if self._capture is not None and self._variant is not None:
            self._capture.capture(source, self._variant)

    def _capture_after(self, seconds: int) -> None:
        if self._capture is not None:
            self._capture.set_delay(seconds)
            self._take_image(CaptureSource.DELAYED)

    def _ask_delay(self) -> None:
        if self._capture is None:
            return
        seconds, chosen = QInputDialog.getInt(
            self, "Capture after a delay", "Seconds before the capture:", self._capture.delay, 1, MAX_DELAY
        )
        if chosen:
            self._capture_after(seconds)

    # Test

    def _show_test(self) -> None:
        test, store = self._test, self._store
        testing = test is not None and store.mode is Mode.TEST
        self.top_bar.set_testing(testing)
        self.top_bar.show_testing(testing and test is not None and test.is_running() and not test.is_capturing())
        self._cancel_test.setEnabled(testing and test is not None and test.is_running())
        if test is None or not testing:
            return
        self.top_bar.test_source.set_source(test.source, test.delay, test.initial_error)
        self.top_bar.test_source.setEnabled(not test.is_running())
        controls = self.top_bar.test_controls
        controls.set_code(bool(store.document.code_overrides), store.include_code)
        controls.set_scope(store.test_scope)
        controls.set_run(test.blocked())
        self.top_bar.show_capturing(test.is_capturing())
        self.top_bar.show_error(test.error)

    def _test_after(self, seconds: int) -> None:
        if self._test is not None:
            self._test.set_delay(seconds)
            self._test.capture(CaptureSource.DELAYED)

    def _ask_test_delay(self) -> None:
        if self._test is None:
            return
        seconds, chosen = QInputDialog.getInt(
            self, "Capture after a delay", "Seconds before the capture:", self._test.delay, 1, MAX_DELAY
        )
        if chosen:
            self._test_after(seconds)

    # Tools

    def _show_tool(self) -> None:
        tool = self.view.tool
        self.tools.show_tool(tool)
        self.top_bar.show_help(HELP.get(tool))
        if tool is Tool.MATCH_AREA:
            variant = self._store.document.get(self._variant) if self._variant is not None else None
            self._edited = variant.match_area if isinstance(variant, ImageVariant) else None
            if self._edited is not None:
                self.view.set_region(Region.of(self._edited))
            self.region_panel.set_action("Apply")
        elif tool is Tool.CROP:
            self.region_panel.set_action("Crop")
        self._place_region_panel()

    def _edit_match_area(self) -> None:
        self.view.set_tool(Tool.MATCH_AREA)
        self.view.setFocus(Qt.FocusReason.OtherFocusReason)  # for Enter and Esc

    def _place_region_panel(self) -> None:
        rect = self.view.region_rect()
        self.region_panel.setVisible(rect is not None)
        if rect is None:
            return
        warning = None
        region = self.view.region()
        variant = self._store.document.get(self._variant) if self._variant is not None else None
        if self.view.tool is Tool.CROP and region is not None and isinstance(variant, ImageVariant):
            warning = crop_warning(variant, region.area())
        self.region_panel.show_warning(warning)
        self.region_panel.place(rect)

    def _apply_region(self) -> None:
        tool, region = self.view.tool, self.view.region()
        if self._variant is None or region is None or tool not in REGION_TOOLS:
            return
        if tool is Tool.MATCH_AREA:
            self._store.set_match_area(self._variant, region.area())
        else:
            self._store.crop(self._variant, region.area())  # the new image closes the edit
        self.view.set_tool(Tool.SELECT)

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


def crop_warning(variant: ImageVariant, crop: Area) -> str | None:
    """Warning on the targets inside the image that a crop would leave outside, or None."""
    if variant.image is None:
        return None
    height, width = variant.image.shape[:2]
    crop = intersect(crop, whole(width, height)) or crop
    image = whole(width, height)
    left = [
        (number, target.name)
        for number, target in enumerate(variant.targets or [], start=1)
        if is_inside(target, image) and not is_inside(target, crop)
    ]
    if not left:
        return None
    if len(left) > 1:
        return f"{len(left)} targets will be outside the image"
    number, name = left[0]
    return f"Target “{name}” will be outside the image" if name else f"Target {number} will be outside the image"


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
