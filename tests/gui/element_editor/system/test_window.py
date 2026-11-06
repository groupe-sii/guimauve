import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor.system import (
    Platform,
    cover_screen,
    hide_under,
    is_excluded_from_capture,
    keep_on_top,
    out_of_capture,
    show_again,
    show_without_focus,
)
from guimauve.gui.element_editor.system import window as window_module


@pytest.fixture(autouse=True)
def no_delay(monkeypatch):
    monkeypatch.setattr(window_module, "HIDE_DELAY_MS", 0)
    monkeypatch.setattr(window_module, "EXCLUDE_DELAY_MS", 0)


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
    """Pretends to run on native Windows, where the exclusion succeeds; records the calls, (hwnd, excluded)."""
    calls: list[tuple[int, bool]] = []
    monkeypatch.setattr(window_module, "current_platform", lambda: Platform.WINDOWS)
    monkeypatch.setattr(
        window_module.windows, "set_excluded_from_capture", lambda hwnd, on: calls.append((hwnd, on)) or True
    )
    return calls


def test_windows_are_excluded_only_during_the_capture(make_window, win32):
    window = make_window()
    assert not is_excluded_from_capture(window)

    with out_of_capture([window]):
        assert is_excluded_from_capture(window)
        assert window.isVisible()

    assert not is_excluded_from_capture(window)
    assert [on for _, on in win32] == [True, False]


def test_windows_hidden_when_the_exclusion_fails(make_window):
    shown, hidden = make_window(), make_window(visible=False)

    with out_of_capture([shown, hidden]):
        assert [w.isVisible() for w in (shown, hidden)] == [False, False]

    assert [w.isVisible() for w in (shown, hidden)] == [True, False]


def test_hidden_windows_are_not_excluded(make_window, win32):
    with out_of_capture([make_window(visible=False)]):
        pass

    assert win32 == []


@pytest.mark.parametrize("excluding", [True, False])
def test_windows_come_back_after_an_error(make_window, request, excluding):
    if excluding:
        request.getfixturevalue("win32")
    window = make_window()

    with pytest.raises(RuntimeError), out_of_capture([window]):
        raise RuntimeError

    assert window.isVisible()
    assert not is_excluded_from_capture(window)


def test_keep_on_top_keeps_the_window_visible(make_window):
    window = make_window()
    keep_on_top(window)
    assert window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert window.isVisible()


def test_keep_on_top_during_a_capture_keeps_the_exclusion(make_window, win32):
    window = make_window()

    with out_of_capture([window]):
        keep_on_top(window)
        assert is_excluded_from_capture(window)

    assert [on for _, on in win32] == [True, True, False]


@pytest.mark.parametrize(
    ("platform", "full_screen"),
    [(Platform.X11, True), (Platform.WAYLAND, True), (Platform.WINDOWS, False), (Platform.OTHER, False)],
)
def test_cover_screen_goes_full_screen_on_linux(make_window, monkeypatch, platform, full_screen):
    """Linux window managers keep an ordinary window out of the panels, such as the top bar of Xfce."""
    monkeypatch.setattr(window_module, "current_platform", lambda: platform)
    window = make_window(visible=False)

    cover_screen(window)

    assert window.isVisible()
    assert window.isFullScreen() is full_screen


def test_windows_under_the_overlays_are_hidden_on_linux_then_shown_again(make_window, monkeypatch):
    """xfwm keeps the editor, which stays on top, above the full screen overlays."""
    monkeypatch.setattr(window_module, "current_platform", lambda: Platform.X11)
    editor, overlay, closed = make_window(), make_window(), make_window(visible=False)

    hidden = hide_under([overlay])

    assert editor in hidden and overlay not in hidden and closed not in hidden
    assert not editor.isVisible() and overlay.isVisible()
    show_again(hidden)
    assert editor.isVisible() and not closed.isVisible()


def test_windows_under_the_overlays_stay_on_windows(make_window, win32):
    editor, overlay = make_window(), make_window()

    assert hide_under([overlay]) == []
    assert editor.isVisible()


def test_show_without_focus(make_window):
    window = make_window(visible=False)
    show_without_focus(window)
    assert window.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    assert window.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert window.isVisible()


def test_wait_until_hidden_leaves_the_system_the_hide_delay(monkeypatch):
    waits: list[int] = []
    monkeypatch.setattr(window_module, "_wait", waits.append)

    window_module.wait_until_hidden()

    assert waits == [window_module.HIDE_DELAY_MS]
