import cv2 as cv
import numpy as np
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QToolButton,
    QWidget,
    QWidgetAction,
)

from guimauve.gui.element_editor_next.panels import TextCentre, VariantList
from guimauve.gui.element_editor_next.panels import variant_list as module
from guimauve.gui.element_editor_next.panels.variant_list import UNREADABLE, drop_index
from guimauve.gui.element_editor_next.services import CaptureSource
from guimauve.models.variant import ImageVariant, TextVariant


@pytest.fixture
def show(theme, tmp_path, qtbot):
    def make(store, capture=None) -> VariantList:
        settings = QSettings(str(tmp_path / "editor.ini"), QSettings.Format.IniFormat)
        panel = VariantList(store, theme, settings, capture)
        qtbot.addWidget(panel)
        panel.resize(panel.width(), 600)
        panel.show()
        return panel

    return make


def names(store) -> list[str]:
    return [variant.name for variant in store.document.variants]


def tool(panel, tooltip: str) -> QToolButton:
    return next(b for b in panel.findChildren(QToolButton) if b.toolTip().startswith(tooltip))


def focused_list(panel) -> QListWidget:
    lst = panel.findChild(QListWidget)
    lst.setFocus()
    return lst


@pytest.mark.parametrize(
    ("source", "row", "below", "expected"),
    [(0, 2, False, 1), (0, 2, True, 2), (2, 0, False, 0), (2, 0, True, 1), (0, -1, False, 2), (1, 1, True, 1)],
)
def test_drop_index(source, row, below, expected):
    assert drop_index(source, row, below, 3) == expected


def test_dropped_row_moves_through_the_store(store, show):
    panel = show(store)

    panel.findChild(QListWidget).dropped.emit(0, 1)

    assert names(store) == ["dark", "light"]


def test_buttons_disabled_when_they_do_not_apply(store, show):
    panel = show(store)

    assert not tool(panel, "Move up").isEnabled()
    assert tool(panel, "Move down").isEnabled()
    store.select(store.variant_keys()[1])
    assert tool(panel, "Move up").isEnabled()
    assert not tool(panel, "Move down").isEnabled()


def test_buttons_disabled_without_variant(make_store, show):
    panel = show(make_store([], x=1))

    for tooltip in ("Duplicate", "Move up", "Move down", "Delete"):
        assert not tool(panel, tooltip).isEnabled()


def test_tooltips_show_the_shortcuts(store, show):
    panel = show(store)

    assert tool(panel, "Duplicate").toolTip() == "Duplicate (Ctrl+D)"
    assert tool(panel, "Move down").toolTip() == "Move down (Alt+Down)"


@pytest.mark.parametrize(
    ("key", "modifier", "expected"),
    [
        (Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier, ["light", "LIGHT_COPY", "dark"]),
        (Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier, ["dark", "light"]),
        (Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier, ["dark"]),
    ],
)
def test_shortcuts_of_the_list(store, show, qtbot, key, modifier, expected):
    panel = show(store)

    qtbot.keyClick(focused_list(panel), key, modifier)

    assert names(store) == expected


def test_delete_while_renaming_edits_the_name(store, show, qtbot):
    panel = show(store)
    lst = focused_list(panel)
    qtbot.keyClick(lst, Qt.Key.Key_F2)

    qtbot.keyClick(lst.focusWidget() or lst, Qt.Key.Key_Delete)

    assert names(store) == ["light", "dark"]


def test_move_with_the_buttons(store, show):
    panel = show(store)

    tool(panel, "Move down").click()

    assert names(store) == ["dark", "light"]
    assert store.selected_variant == store.variant_keys()[1]


def test_add_text(qtbot, store, show):
    panel = show(store)

    with qtbot.waitSignal(store.text_edit_requested):
        panel.add_text()

    added = store.document.variants[-1]
    assert isinstance(added, TextVariant) and added.name == "VARIANT_1"
    assert store.selected_variant == store.document.key(added)


def test_find_a_text_in_the_add_menu_leaves_the_focus_in_the_text(qtbot, theme, store, tmp_path):
    window = QWidget()
    qtbot.addWidget(window)
    panel = VariantList(store, theme, QSettings(str(tmp_path / "editor.ini"), QSettings.Format.IniFormat))
    centre = TextCentre(store, theme)
    layout = QHBoxLayout(window)
    layout.addWidget(panel)
    layout.addWidget(centre)
    window.show()
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    panel.findChild(QListWidget).setFocus()
    menu = panel.findChild(QToolButton, "add").menu()
    menu.popup(panel.mapToGlobal(panel.rect().center()))
    qtbot.waitExposed(menu)

    menu.setActiveAction(next(action for action in menu.actions() if action.text() == "Find a text"))
    qtbot.keyClick(menu, Qt.Key.Key_Return)  # closes the menu, as a click would
    qtbot.waitUntil(lambda: not menu.isVisible())

    assert QApplication.focusWidget() is centre.field.input


def test_import_image(store, show, monkeypatch, tmp_path):
    path = tmp_path / "button.png"
    cv.imwrite(str(path), np.zeros((8, 16, 3), np.uint8))
    monkeypatch.setattr(module, "ask_image_file", lambda parent: path)
    panel = show(store)

    panel.import_image()

    added = store.document.variants[-1]
    assert isinstance(added, ImageVariant) and added.image.shape == (8, 16, 3)


def test_import_of_an_unreadable_file(store, show, monkeypatch, tmp_path):
    (tmp_path / "notes.png").write_text("not an image")
    warnings: list[str] = []
    monkeypatch.setattr(module, "ask_image_file", lambda parent: tmp_path / "notes.png")
    monkeypatch.setattr(module, "warn", lambda parent, text: warnings.append(text))
    panel = show(store)

    panel.import_image()

    assert warnings == [UNREADABLE]
    assert names(store) == ["light", "dark"]


def test_import_cancelled(store, show, monkeypatch):
    monkeypatch.setattr(module, "ask_image_file", lambda parent: None)

    show(store).import_image()

    assert not store.can_undo


def test_add_menu_offers_the_captures_disabled(store, show):
    panel = show(store)
    menu = panel.findChild(QToolButton, "add").menu()

    texts = {
        action.text(): action.isEnabled()
        for action in menu.actions()
        if not action.isSeparator() and not isinstance(action, QWidgetAction)
    }

    assert all(not action.icon().isNull() for action in menu.actions() if action.text())
    assert texts == {
        "Initial screen": False,
        "Instant": False,
        "After a delay…": False,
        "Import a file…": True,
        "Find a text": True,
    }


def test_empty_state_buttons(make_store, show):
    store = make_store([], x=1)
    panel = show(store)

    next(b for b in panel.findChildren(QPushButton) if b.text() == "Find a text").click()

    assert len(store.document.variants) == 1


def test_add_menu_has_a_visible_title(store, show):
    menu = show(store).findChild(QToolButton, "add").menu()

    (title,) = [action for action in menu.actions() if isinstance(action, QWidgetAction)]

    assert title.defaultWidget().text() == "Capture an image"
    assert not title.isEnabled()


def press(lst, widget, qtbot):
    qtbot.mousePress(
        lst.viewport(), Qt.MouseButton.LeftButton, pos=widget.mapTo(lst.viewport(), widget.rect().center())
    )


@pytest.mark.parametrize(("on_grip", "dragged"), [(True, True), (False, False)])
def test_drag_starts_only_from_the_grip(store, show, qtbot, monkeypatch, on_grip, dragged):
    panel = show(store)
    lst = panel.findChild(QListWidget)
    started: list[bool] = []
    monkeypatch.setattr(module.QDrag, "exec", lambda self, *args: started.append(True))
    row = panel.rows()[1]
    press(lst, row.grip if on_grip else row.thumbnail, qtbot)

    lst.startDrag(Qt.DropAction.MoveAction)

    assert bool(started) is dragged


def test_no_grip_when_collapsed(store, show):
    panel = show(store)

    panel.set_collapsed(True)

    assert all(not hasattr(row, "grip") for row in panel.rows())


class _Flow:
    """Capture flow recording what it is asked."""

    def __init__(self, initial_error=None):
        self.initial_error = initial_error
        self.asked = []

    def capture(self, source, variant):
        self.asked.append((source, variant))


@pytest.mark.parametrize(
    ("text", "source"),
    [
        ("Initial screen", CaptureSource.INITIAL),
        ("Instant", CaptureSource.INSTANT),
        ("After a delay…", CaptureSource.DELAYED),
    ],
)
def test_captures_add_a_new_variant(store, show, text, source):
    flow = _Flow()
    menu = show(store, flow).findChild(QToolButton, "add").menu()

    next(action for action in menu.actions() if action.text() == text).trigger()

    assert flow.asked == [(source, None)]


def test_initial_screen_unavailable(store, show):
    menu = show(store, _Flow("No display")).findChild(QToolButton, "add").menu()

    initial = next(action for action in menu.actions() if action.text() == "Initial screen")

    assert not initial.isEnabled()
    assert initial.toolTip() == "No display"
