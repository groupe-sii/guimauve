import numpy as np
import pytest
from PySide6.QtCore import QPoint, Qt

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.overlays.test_session import TestViewSession
from guimauve.gui.element_editor_next.overlays.test_view import ScreenView, TestView, ViewMatch
from guimauve.gui.element_editor_next.system import ScreenMap


def view(number: int = 1, matches=()) -> ScreenView:
    return ScreenView(number, np.zeros((100, 200, 3), np.uint8), True, None, None, tuple(matches))


MATCH = ViewMatch(0, ((20, 20), (60, 20), (60, 40), (20, 40)), (40, 30), True)


@pytest.fixture
def window(qtbot):
    widget = TestView(view(matches=[MATCH]), "Test result")
    qtbot.addWidget(widget)
    widget.resize(200, 100)
    widget.show()
    return widget


def test_esc_or_a_click_closes(window, qtbot):
    with qtbot.waitSignal(window.closed):
        qtbot.keyClick(window, Qt.Key.Key_Escape)
    with qtbot.waitSignal(window.closed):
        qtbot.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(150, 80))


def test_the_match_under_the_cursor_is_hovered(window, qtbot):
    qtbot.mouseMove(window, QPoint(40, 30))
    qtbot.waitUntil(lambda: window.hovered == 0)

    qtbot.mouseMove(window, QPoint(150, 80))
    qtbot.waitUntil(lambda: window.hovered is None)


def test_session_opens_a_window_per_screen_and_closes_them_together(qtbot):
    screens = ScreenMap([Screen(0, 0, 400, 100), Screen(0, 0, 200, 100), Screen(200, 0, 200, 100)], [])
    session = TestViewSession([view(1), view(2, [MATCH])], screens, "Test result", focused=0)
    session.start()
    windows = list(session.windows.values())
    for window in windows:
        qtbot.addWidget(window)

    assert len(windows) == 2 and all(window.isVisible() for window in windows)

    with qtbot.waitSignal(session.finished):
        windows[0].closed.emit()
    assert session.windows == {} and not any(window.isVisible() for window in windows)


@pytest.fixture
def large(qtbot):
    def make(*matches) -> TestView:
        widget = TestView(ScreenView(2, np.zeros((300, 400, 3), np.uint8), True, None, None, matches), "Test result")
        qtbot.addWidget(widget)
        widget.resize(400, 300)
        widget.show_number(2)
        widget.show()
        return widget

    return make


def box(left: int, top: int, right: int, bottom: int) -> ViewMatch:
    corners = ((left, top), (right, top), (right, bottom), (left, bottom))
    return ViewMatch(0, corners, ((left + right) // 2, (top + bottom) // 2), True)


def test_the_banner_goes_down_away_from_a_match(large):
    assert large().banner_rect().top() < 150

    assert large(box(150, 5, 250, 40)).banner_rect().top() > 150


def test_the_number_of_the_screen_leaves_a_corner_with_a_match(large):
    free = large().number_rect()
    assert free.left() < 200 and free.top() > 150  # bottom left

    moved = large(box(5, 250, 60, 295)).number_rect()
    assert moved.left() > 200 and moved.top() > 150  # bottom right


def test_the_number_of_the_screen_keeps_away_from_the_cursor(large, qtbot):
    widget = large()

    qtbot.mouseMove(widget, QPoint(20, 280))

    qtbot.waitUntil(lambda: widget.number_rect().left() > 200)
