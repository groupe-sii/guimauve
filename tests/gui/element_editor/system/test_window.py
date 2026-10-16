import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.system import (
    Platform,
    exclude_from_capture,
    hidden_during_capture,
    is_excluded_from_capture,
    keep_on_top,
    show_without_focus,
)
from guimauve.gui.element_editor_next.system import window as window_module


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    monkeypatch.setattr(window_module, "HIDE_DELAY_MS", 0)


@pytest.fixture
def make_window(qtbot):
    def make(visible: bool = True) -> QWidget:
        window = QWidget()
        qtbot.addWidget(window)
        window.setVisible(visible)
        return window

    return make


@pytest.fixture
def win32(monkeypatch):
    """Pretends to run on native Windows, where the exclusion succeeds; records the windows excluded."""
    calls: list[int] = []
    monkeypatch.setattr(window_module, "current_platform", lambda: Platform.WINDOWS)
    monkeypatch.setattr(window_module.windows, "exclude_from_capture", lambda hwnd: calls.append(hwnd) or True)
    return calls


def test_exclusion_fails_without_native_window(make_window):
    window = make_window()
    assert not exclude_from_capture(window)
    assert not is_excluded_from_capture(window)


def test_exclusion_succeeds_on_windows(make_window, win32):
    window = make_window()
    assert exclude_from_capture(window)
    assert is_excluded_from_capture(window)


def test_hidden_during_capture_hides_only_visible_windows_not_excluded(make_window, win32):
    shown, hidden, excluded = make_window(), make_window(visible=False), make_window()
    exclude_from_capture(excluded)

    with hidden_during_capture([shown, hidden, excluded]):
        assert [w.isVisible() for w in (shown, hidden, excluded)] == [False, False, True]

    assert [w.isVisible() for w in (shown, hidden, excluded)] == [True, False, True]


def test_hidden_windows_come_back_after_an_error(make_window):
    window = make_window()
    with pytest.raises(RuntimeError), hidden_during_capture([window]):
        raise RuntimeError
    assert window.isVisible()


def test_keep_on_top_keeps_the_window_visible(make_window):
    window = make_window()
    keep_on_top(window)
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert window.isVisible()


def test_keep_on_top_applies_the_exclusion_again(make_window, win32):
    window = make_window()
    exclude_from_capture(window)
    keep_on_top(window)
    assert len(win32) == 2
    assert is_excluded_from_capture(window)


def test_show_without_focus(make_window):
    window = make_window(visible=False)
    show_without_focus(window)
    assert window.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert window.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert window.isVisible()
