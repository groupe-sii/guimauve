import threading
import time
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QElapsedTimer, QTimer

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.services import SearchProcess, TestRunner
from guimauve.gui.element_editor_next.services.search_process import LOST
from guimauve.gui.element_editor_next.state import Document, TestScope, resolve_element
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters
from guimauve.models.variant import ImageVariant

HERE = [str(Path(__file__).parent)]
SCREENS = [Screen(0, 0, 60, 40), Screen(0, 0, 60, 40)]


@pytest.fixture
def make_process():
    processes: list[SearchProcess] = []

    def make(locate: str | None = None) -> SearchProcess:
        process = SearchProcess(locate, HERE) if locate else SearchProcess()
        processes.append(process)
        return process

    yield make
    for process in processes:
        process.close()


def screen_with_button() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    screen = rng.integers(0, 255, (40, 60, 3), dtype=np.uint8)
    return screen, screen[10:22, 20:40].copy()


def test_finds_the_element_in_the_process(make_process):
    screen, needle = screen_with_button()
    raw = Element(name="button", variants=[ImageVariant(name="BUTTON", image=needle)])
    element = resolve_element(Document(raw, {}), Parameters().default)

    report, seconds = make_process().search(element, {1: screen}, SCREENS, (0, 0))

    assert [tuple(match.target) for match in report.matches] == [(30, 16)]
    assert report.match_screens == [1] and seconds > 0


def test_a_stopped_search_ends(make_process):
    process = make_process("busy_search:until_stopped")
    process.start()

    def stop_soon():
        time.sleep(0.2)
        process.stop()

    threading.Thread(target=stop_soon).start()
    with pytest.raises(RuntimeError, match="^stopped$"):
        process.search(Element(name="button"), {1: np.zeros((4, 4, 3), np.uint8)}, [], (0, 0))


def test_a_lost_process_fails_the_search_then_starts_again(make_process):
    process = make_process("busy_search:crash")
    capture = {1: np.zeros((4, 4, 3), np.uint8)}

    with pytest.raises(RuntimeError, match=LOST):
        process.search(Element(name="button"), capture, [], (0, 0))
    with pytest.raises(RuntimeError, match=LOST):  # a new process, which crashes as well
        process.search(Element(name="button"), capture, [], (0, 0))


def test_the_window_keeps_running_during_a_search(make_process, qtbot):
    process = make_process("busy_search:hold")
    process.start()
    runner = TestRunner((0, 0), process=process)
    gaps: list[int] = []
    clock = QElapsedTimer()
    clock.start()
    timer = QTimer()
    timer.timeout.connect(lambda: gaps.append(clock.restart()))
    timer.start(10)

    with qtbot.waitSignal(runner.finished, timeout=20000):
        runner.run(Element(name="button"), {1: np.zeros((4, 4, 3), np.uint8)}, [], TestScope.ELEMENT, None, True)
    timer.stop()
    runner.shutdown()

    assert runner.result.error is None and runner.result.duration > 0.2  # the search did hold for a while
    assert max(gaps) < 200  # while the timer of the window kept ticking


def test_no_process_starts_once_closed(make_process):
    process = make_process()
    process.close()

    with pytest.raises(RuntimeError, match=LOST):
        process.start()
