from contextlib import contextmanager

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QFont, QKeySequence, QMouseEvent, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from guimauve.gui.element_editor_next.canvas import HELP, Region, Tool
from guimauve.gui.element_editor_next.canvas.top_bar import ACTUAL_SIZE, FIT, ZOOM_IN, ZOOM_IN_EXTRA, ZOOM_OUT
from guimauve.gui.element_editor_next.components import CHECK
from guimauve.gui.element_editor_next.panels import CanvasPanel, CaptureFlow
from guimauve.gui.element_editor_next.panels.canvas_panel import EMPTY_TITLE, crop_warning
from guimauve.gui.element_editor_next.services import CaptureService
from guimauve.gui.element_editor_next.services import capture as capture_module
from guimauve.gui.element_editor_next.state import ELEMENT
from guimauve.gui.element_editor_next.system import ScreenMap
from guimauve.gui.element_editor_next.theme import METRICS
from guimauve.models.area import Area
from guimauve.models.variant import ImageVariant


@pytest.fixture
def show(theme, qtbot):
    def make(store) -> CanvasPanel:
        panel = CanvasPanel(store, theme)
        qtbot.addWidget(panel)
        panel.resize(660, 410)
        panel.show()
        return panel

    return make


def key(store, index: int) -> int:
    return store.variant_keys()[index]


def action(panel, text: str):
    return next(a for a in panel.top_bar.zoom_menu.actions() if a.text().split("\t")[0] == text)


def hover(panel, pixel: QPointF) -> None:
    point = panel.view.viewportTransform().map(pixel)
    event = QMouseEvent(
        QEvent.Type.MouseMove,
        point,
        panel.view.viewport().mapToGlobal(point),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(panel.view.viewport(), event)


def test_shows_the_image_of_the_selected_variant(store, show):
    store.replace_image(key(store, 1), np.zeros((30, 50, 3), np.uint8))

    panel = show(store)
    assert panel.view.image().width() == 120

    store.select(key(store, 1))
    assert (panel.view.image().width(), panel.view.image().height()) == (50, 30)


def test_a_new_image_fits_again(store, show):
    panel = show(store)
    panel.view.set_zoom(4.0)

    store.crop(key(store, 0), Area(left=0, top=0, right=60, bottom=40))

    assert panel.view.is_fitting()
    assert panel.view.image().width() == 60


def test_other_edits_keep_the_zoom(store, show):
    panel = show(store)
    panel.view.set_zoom(4.0)

    store.set_field(ELEMENT, "timeout", 9)
    store.move_target(store.document.key(store.document.variants[0].targets[0]), 50, 30)

    assert panel.view.zoom == 4.0


def test_variant_without_image_shows_how_to_capture(make_store, show):
    panel = show(make_store([ImageVariant(name="empty")]))

    assert panel.empty.isVisible()
    assert panel.view.image() is None
    assert not panel.top_bar.zoom_button.isVisible()
    assert EMPTY_TITLE in [label.text() for label in panel.empty.findChildren(QLabel)]


def test_text_variant_shows_the_background_only(store, show, text_variant):
    store.add_variant(text_variant)

    panel = show(store)

    assert not panel.empty.isVisible()
    assert panel.view.image() is None
    assert not panel.status_bar.size_label.isVisible()


def test_status_bar_shows_the_image_and_the_pixel(store, show):
    store.replace_image(key(store, 0), np.full((40, 120, 3), (45, 107, 216), np.uint8))
    panel = show(store)
    status = panel.status_bar

    assert status.size_label.text() == "Image 120 × 40 px"
    assert status.position.text() == "–"
    assert not status.color.isVisible()

    hover(panel, QPointF(12.5, 7.5))

    assert status.position.text() == "x 12, y 7"
    assert status.color.text() == "#2D6BD8"
    assert status.color.isVisible()


def test_numbers_use_tabular_digits(store, show):
    panel = show(store)

    for widget in (panel.status_bar.position, panel.status_bar.size_label, panel.top_bar.zoom_button):
        assert widget.font().featureValue(QFont.Tag("tnum")) == 1


def test_zoom_menu(store, show):
    panel = show(store)

    action(panel, "200 %").trigger()
    assert panel.view.zoom == 2.0
    assert panel.top_bar.zoom_button.text() == "200 %"

    action(panel, "Actual size (100 %)").trigger()
    assert panel.view.zoom == 1.0

    action(panel, "Fit to window").trigger()
    assert panel.view.is_fitting()


def test_zoom_buttons(store, show):
    panel = show(store)
    panel.view.set_zoom(1.0)

    panel.top_bar.zoom_in.click()
    assert panel.view.zoom == 1.5

    panel.top_bar.zoom_out.click()
    panel.top_bar.zoom_out.click()
    assert panel.view.zoom == 0.75


def test_zoom_shortcuts_are_bound(store, show):
    panel = show(store)

    keys = {shortcut.key() for shortcut in panel.findChildren(QShortcut)}

    assert keys >= {QKeySequence(k) for k in (FIT, ACTUAL_SIZE, ZOOM_IN, ZOOM_IN_EXTRA, ZOOM_OUT)}


def targets(store) -> list[int]:
    return [store.document.key(target) for target in store.document.variants[0].targets]


def markers(panel) -> dict[int, object]:
    return {item.marker.key: item.marker for item in panel.view.target_items()}


def test_shows_the_targets_of_the_variant(store, show):
    store.move_target(targets(store)[1], 200, 5)  # outside the 120 × 40 image
    panel = show(store)

    shown = markers(panel)

    assert [(m.number, m.name, m.x, m.y, m.outside) for m in shown.values()] == [
        (1, "icon", 10, 20, False),
        (2, "arrow", 200, 5, True),
    ]


def test_target_used_is_the_default_target(store, show):
    store.set_field(key(store, 0), "default_target", "arrow")
    panel = show(store)

    assert [m.used for m in markers(panel).values()] == [False, True]


def test_target_property_wins_over_the_default_target(store, show):
    store.set_field(key(store, 0), "default_target", "arrow")
    store.set_field(ELEMENT, "target", "icon")
    panel = show(store)

    assert [m.used for m in markers(panel).values()] == [True, False]


def test_first_unnamed_target_is_used_without_name(store, show):
    store.rename_target(key(store, 0), targets(store)[1], None)

    panel = show(store)

    assert [m.used for m in markers(panel).values()] == [False, True]


def test_no_target_used_for_a_name_not_found(store, show):
    store.set_field(ELEMENT, "target", "missing")
    store.rename_target(key(store, 0), targets(store)[1], None)

    panel = show(store)

    assert [m.used for m in markers(panel).values()] == [False, False]


def test_selection_follows_the_store(store, show):
    panel = show(store)

    store.select(key(store, 0), targets(store)[1])

    assert [m.selected for m in markers(panel).values()] == [False, True]


def test_drag_selects_and_moves_the_target_in_one_step(store, show):
    panel = show(store)
    view, target = panel.view, targets(store)[0]

    view.target_pressed.emit(target)
    for x in (20, 30, 40):
        view.target_dragged.emit(target, x, 25)
    view.target_released.emit(target)

    moved = store.document.variants[0].targets[0]
    assert store.selected_target == target
    assert (moved.x, moved.y) == (40, 25)
    store.undo()
    assert (moved.x, moved.y) == (10, 20)
    assert not store.can_undo


def test_click_on_the_background_deselects_the_target(store, show):
    panel = show(store)
    store.select(key(store, 0), targets(store)[0])

    panel.view.background_clicked.emit()

    assert (store.selected_variant, store.selected_target) == (key(store, 0), None)


def test_nudge_and_delete_the_selected_target(store, show):
    panel = show(store)
    store.select(key(store, 0), targets(store)[0])

    panel.view.nudge_requested.emit(10, -1)
    assert (store.document.variants[0].targets[0].x, store.document.variants[0].targets[0].y) == (20, 19)

    panel.view.delete_requested.emit()
    assert [t.name for t in store.document.variants[0].targets] == ["arrow"]
    assert store.selected_target is None


def test_keys_do_nothing_without_selected_target(store, show):
    panel = show(store)

    panel.view.nudge_requested.emit(1, 0)
    panel.view.delete_requested.emit()

    assert not store.can_undo


def test_click_in_the_target_tool_adds_and_selects_a_target(store, show):
    panel = show(store)

    panel.view.target_added.emit(-4, 12)

    added = store.document.variants[0].targets[-1]
    assert (added.name, added.x, added.y) == (None, -4, 12)
    assert store.selected_target == store.document.key(added)
    assert markers(panel)[store.document.key(added)].outside


def test_toolbar_chooses_the_tool_and_shows_help(store, show):
    panel = show(store)
    assert not panel.top_bar.help.isVisible()

    panel.tools.button(Tool.TARGET).click()

    assert panel.view.tool is Tool.TARGET
    assert panel.top_bar.help.text() == HELP[Tool.TARGET]
    panel.view.set_tool(Tool.SELECT)
    assert panel.tools.button(Tool.SELECT).isChecked()
    assert not panel.top_bar.help.isVisible()


def test_no_tools_without_image(make_store, show):
    panel = show(make_store([ImageVariant(name="empty")]))

    assert not panel.tools.isVisible()


def test_match_area_is_drawn(store, show):
    store.set_match_area(key(store, 0), Area(left=2, top=3, right=40, bottom=30))

    panel = show(store)

    assert panel.view.match_area() == Region(2, 3, 40, 30)


def test_match_area_tool_starts_from_the_match_area(store, show):
    store.set_match_area(key(store, 0), Area(left=2, top=3, right=40, bottom=30))
    panel = show(store)

    panel.view.set_tool(Tool.MATCH_AREA)

    assert panel.view.region() == Region(2, 3, 40, 30)
    assert panel.region_panel.isVisible()
    assert panel.region_panel.apply.text() == "Apply"
    assert panel.top_bar.help.text() == HELP[Tool.MATCH_AREA]


def test_apply_sets_the_match_area(store, show):
    panel = show(store)
    panel.view.set_tool(Tool.MATCH_AREA)
    panel.view.set_region(Region(5, 6, 50, 30))

    panel.region_panel.apply.click()

    assert store.document.variants[0].match_area == Area(left=5, top=6, right=50, bottom=30)
    assert panel.view.tool is Tool.SELECT
    assert not panel.region_panel.isVisible()


def test_enter_applies(store, show):
    panel = show(store)
    panel.view.set_tool(Tool.MATCH_AREA)
    panel.view.set_region(Region(5, 6, 50, 30))

    panel.view.region_confirmed.emit()

    assert store.document.variants[0].match_area == Area(left=5, top=6, right=50, bottom=30)


def test_cancel_keeps_the_match_area(store, show):
    panel = show(store)
    panel.view.set_tool(Tool.MATCH_AREA)
    panel.view.set_region(Region(5, 6, 50, 30))

    panel.region_panel.cancel.click()

    assert store.document.variants[0].match_area is None
    assert panel.view.tool is Tool.SELECT


def test_edit_requested_from_the_store(store, show):
    panel = show(store)

    store.request_match_area_edit()

    assert panel.view.tool is Tool.MATCH_AREA


def test_edit_closes_when_the_match_area_changes(store, show):
    store.set_match_area(key(store, 0), Area(left=2, top=3, right=40, bottom=30))
    panel = show(store)
    panel.view.set_tool(Tool.MATCH_AREA)

    store.undo()

    assert panel.view.tool is Tool.SELECT


def test_edit_closes_with_another_variant(store, show):
    panel = show(store)
    panel.view.set_tool(Tool.MATCH_AREA)

    store.select(key(store, 1))

    assert panel.view.tool is Tool.SELECT
    assert not panel.region_panel.isVisible()


@pytest.mark.parametrize(
    ("crop", "expected"),
    [
        (Area(left=0, top=0, right=120, bottom=40), None),
        (Area(left=0, top=0, right=20, bottom=40), "Target “arrow” will be outside the image"),
        (Area(left=60, top=0, right=120, bottom=40), "2 targets will be outside the image"),
    ],
)
def test_crop_warning(store, crop, expected):
    store.move_target(targets(store)[1], 30, 20)

    assert crop_warning(store.document.variants[0], crop) == expected


def test_crop_warning_names_an_unnamed_target_by_its_number(store):
    store.move_target(targets(store)[1], 30, 20)
    store.rename_target(key(store, 0), targets(store)[1], None)

    warning = crop_warning(store.document.variants[0], Area(left=0, top=0, right=20, bottom=40))

    assert warning == "Target 2 will be outside the image"


def test_crop_warning_ignores_targets_already_outside(store):
    store.move_target(targets(store)[1], 500, 20)

    assert crop_warning(store.document.variants[0], Area(left=0, top=0, right=60, bottom=40)) is None


def test_crop_tool(store, show):
    store.move_target(targets(store)[1], 30, 20)
    panel = show(store)

    panel.view.set_tool(Tool.CROP)
    assert panel.view.region() == Region(0, 0, 120, 40)
    assert panel.region_panel.apply.text() == "Crop"
    assert not panel.region_panel.warning.isVisible()

    panel.view.set_region(Region(0, 0, 20, 40))
    assert panel.region_panel.warning.text() == "Target “arrow” will be outside the image"
    assert panel.region_panel.warning.isVisible()


def test_crop_applies(store, show):
    panel = show(store)
    panel.view.set_tool(Tool.CROP)
    panel.view.set_region(Region(5, 0, 65, 40))

    panel.region_panel.apply.click()

    assert store.document.variants[0].image.shape[:2] == (40, 60)
    assert panel.view.tool is Tool.SELECT
    assert panel.view.image().width() == 60
    assert not panel.region_panel.isVisible()


def test_a_single_target_has_no_number(store, show):
    store.remove_target(key(store, 0), targets(store)[1])

    panel = show(store)

    assert [m.number for m in markers(panel).values()] == [None]


def test_hide_switch_hides_the_targets(store, show):
    panel = show(store)

    panel.tools.hide_button.click()

    assert panel.view.overlays_hidden()
    panel.view.set_overlays_hidden(False)
    assert not panel.tools.hide_button.isChecked()


@pytest.fixture
def with_capture(theme, qtbot, tmp_path, monkeypatch):
    @contextmanager
    def out_of_capture(windows):
        yield

    monkeypatch.setattr(capture_module, "out_of_capture", out_of_capture)

    def make(store, initial=True, fail=False) -> CaptureFlow:
        def provider(number):
            if fail:
                raise RuntimeError("Driver lost")
            return np.zeros((50, 80, 3), np.uint8)

        service = CaptureService(provider, ScreenMap([]), tick_ms=1000)
        if initial:
            service.take_initial()
        window = QWidget()
        qtbot.addWidget(window)
        settings = QSettings(str(tmp_path / "editor.ini"), QSettings.Format.IniFormat)
        flow = CaptureFlow(store, service, settings, window, lambda captures: None)
        panel = CanvasPanel(store, theme, flow)
        qtbot.addWidget(panel)
        panel.show()
        return panel, flow

    return make


def menu_action(panel, text: str):
    actions = panel.top_bar.capture_menu.actions()
    return next(a for a in actions if a.text().split("\t")[0].removesuffix(CHECK) == text)


def test_capture_button_names_what_it_does(store, with_capture, make_store):
    panel, _ = with_capture(store)
    assert panel.top_bar.capture_button.isVisible()
    assert panel.top_bar.capture_button.text() == "Recapture"

    empty, _ = with_capture(make_store([ImageVariant(name="empty")]))
    assert empty.top_bar.capture_button.text() == "Capture"


def test_no_capture_for_a_text_variant(store, with_capture, text_variant):
    store.add_variant(text_variant)

    panel, _ = with_capture(store)

    assert not panel.top_bar.capture_button.isVisible()


def test_no_capture_button_without_flow(store, show):
    panel = show(store)

    assert not panel.top_bar.capture_button.isVisible()


def test_initial_screen_disabled_without_initial_captures(store, with_capture):
    panel, _ = with_capture(store, fail=True)

    initial = menu_action(panel, "Initial screen")

    assert not initial.isEnabled()
    assert initial.toolTip() == "Driver lost"


def test_delay_chosen_captures_after_it(store, with_capture):
    panel, flow = with_capture(store)
    later = next(a for a in panel.top_bar.capture_menu.actions() if a.objectName() == "captureLater")

    next(a for a in later.menu().actions() if a.text() == "5 s").trigger()

    assert flow.delay == 5
    assert flow.is_busy()
    assert not panel.top_bar.capture_button.isEnabled()
    flow.cancel()
    assert panel.top_bar.capture_button.isEnabled()


def test_delay_kept_is_ticked(store, with_capture):
    panel, flow = with_capture(store)
    flow.set_delay(10)
    panel._show_capture()

    later = next(a for a in panel.top_bar.capture_menu.actions() if a.objectName() == "captureLater")

    assert later.text().endswith("10 s")
    assert [a.text() for a in later.menu().actions() if a.text().endswith(CHECK)] == ["10 s" + CHECK]


def test_capture_error_in_the_bar(store, with_capture):
    panel, flow = with_capture(store, initial=False, fail=True)

    menu_action(panel, "Instant").trigger()

    assert panel.top_bar.error.text() == "Capture failed: Driver lost"
    assert panel.top_bar.error.isVisible()
    panel.top_bar.close_error.click()
    assert not panel.top_bar.error.isVisible()


def test_minimum_width_does_not_depend_on_the_texts(store, show):
    panel = show(store)

    assert panel.minimumWidth() == METRICS.canvas_min_width
