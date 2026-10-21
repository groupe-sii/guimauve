import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QPushButton

from guimauve.gui.element_editor_next.contract import Context, ResumeMode
from guimauve.gui.element_editor_next.panels import AlertBanner, Header, Inspector
from guimauve.gui.element_editor_next.panels.header import REDO, SAVE, UNDO
from guimauve.gui.element_editor_next.state import ELEMENT
from guimauve.gui.element_editor_next.window import EditorWindow


@pytest.fixture(autouse=True)
def no_dialog(monkeypatch):
    """Closing a modified window at the end of a test never waits on the confirmation."""
    monkeypatch.setattr(EditorWindow, "confirm_discard", lambda self: True)


@pytest.fixture
def open_window(store, theme, tmp_path, qtbot):
    def make(from_run=True, message="Element not found on screen", on=None) -> EditorWindow:
        on = on or store
        context = Context(on.document.element, on.default, lambda screen: None, message, "click", from_run=from_run)
        window = EditorWindow(on, theme, QSettings(str(tmp_path / "editor.ini"), QSettings.Format.IniFormat), context)
        qtbot.addWidget(window)
        window.show()
        return window

    return make


def button(window, text: str) -> QPushButton:
    return next(b for b in window.findChildren(QPushButton) if b.text() == text)


def test_assembles_the_panels(open_window):
    window = open_window()

    assert window.windowTitle() == "button – Guimauve"
    for panel in (Header, AlertBanner, Inspector):
        assert window.findChild(panel) is not None


def test_save_returns_the_edited_element(store, open_window, qtbot):
    window = open_window()
    store.set_field(ELEMENT, "timeout", 9)

    with qtbot.waitSignal(window.finished):
        button(window, "Save and resume").click()

    assert window.result.element.timeout == 9
    assert window.result.resume is ResumeMode.NOW
    assert not window.isVisible()


def shortcut(window, key) -> QShortcut:
    return next(s for s in window.findChildren(QShortcut) if s.key() == QKeySequence(key))


def test_save_shortcut(open_window, qtbot):
    window = open_window()

    with qtbot.waitSignal(window.finished):
        shortcut(window, SAVE).activated.emit()

    assert window.result.element is not None


def test_save_shortcut_blocked_by_an_error(store, open_window):
    window = open_window()
    store.set_field(ELEMENT, "timeout", -1)

    shortcut(window, SAVE).activated.emit()

    assert window.result is None
    assert window.isVisible()


@pytest.mark.parametrize(("key", "timeout"), [(UNDO, None), (REDO, 9)])
def test_undo_and_redo_shortcuts(store, open_window, key, timeout):
    window = open_window()
    store.set_field(ELEMENT, "timeout", 9)
    if key is REDO:
        store.undo()

    shortcut(window, key).activated.emit()

    assert store.document.element.timeout == timeout


def test_skip_returns_nothing(open_window, qtbot):
    window = open_window()

    with qtbot.waitSignal(window.finished):
        button(window, "Skip").click()

    assert window.result.element is None


def test_cancel_from_the_cli(open_window, qtbot):
    window = open_window(from_run=False, message="")

    assert window.findChild(AlertBanner).isHidden()
    with qtbot.waitSignal(window.finished):
        button(window, "Cancel").click()
    assert window.result.element is None


def test_closing_unmodified_needs_no_confirmation(open_window, monkeypatch, qtbot):
    window = open_window()
    monkeypatch.setattr(window, "confirm_discard", pytest.fail)

    with qtbot.waitSignal(window.finished):
        window.close()

    assert window.result.element is None


@pytest.mark.parametrize("discard", [True, False])
def test_closing_modified_asks_first(store, open_window, monkeypatch, discard):
    window = open_window()
    store.set_field(ELEMENT, "timeout", 9)
    monkeypatch.setattr(window, "confirm_discard", lambda: discard)

    window.close()

    assert window.isVisible() is not discard
    assert (window.result is not None) is discard
    window.confirm_discard = lambda: True  # lets the test close it
