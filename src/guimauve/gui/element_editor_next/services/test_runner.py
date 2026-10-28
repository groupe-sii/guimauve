"""Searching the element of the Test mode on captures already taken, in a thread, without any action."""

import threading
import time
from collections.abc import Callable
from dataclasses import replace
from functools import partial
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.state import TestResult, TestScope
from guimauve.models.element import Element

if TYPE_CHECKING:  # the detection loads the OCR models, imported in the thread
    from guimauve.detection.locate import LocateReport

Grab = Callable[[int], np.ndarray]
Stopped = Callable[[], bool]
Locate = Callable[[Element, Grab, list[Screen], tuple[int, int], Stopped], "LocateReport"]


def grabber(captures: dict[int, np.ndarray], screens: list[Screen]) -> Grab:
    """Gives the image of a screen from captures of each screen, as Driver.capture does.

    Screen 0 is made of the captures of the screens, at their place on the desktop, black between them. Without
    screens from the driver, as with VNC or a file, the only capture stands for any screen.

    :param captures: Capture of each screen, by number.
    :param screens: Screens of the driver; empty when unknown.
    """

    def grab(number: int) -> np.ndarray:
        if not screens:
            return next(iter(captures.values()))
        if number == 0:
            return _desktop(captures, screens)
        if number not in captures:
            raise ValueError(f"Screen {number} was not captured")
        return captures[number]

    return grab


def _desktop(captures: dict[int, np.ndarray], screens: list[Screen]) -> np.ndarray:
    bounds = screens[0]
    first = next(iter(captures.values()))
    desktop = np.zeros((bounds.height, bounds.width, *first.shape[2:]), first.dtype)
    for number, image in captures.items():
        screen = screens[number]
        x, y = screen.left - bounds.left, screen.top - bounds.top
        height, width = min(image.shape[0], bounds.height - y), min(image.shape[1], bounds.width - x)
        desktop[y : y + height, x : x + width] = image[:height, :width]
    return desktop


def used_match(report: "LocateReport", index: int) -> tuple[int | None, str | None]:
    """The match a run would use, by its index, or why there is none although some were found.

    :return: The index of the match, None when there is none; the error, None when there is none.
    """
    if not report.matches or report.fixed_position:
        return (0 if report.matches else None), None
    if 0 <= index < len(report.matches):
        return index, None
    count = len(report.matches)
    return None, f"Index {index} out of {count} {'match' if count == 1 else 'matches'}"


class TestRunner(QObject):
    """Searches an element on captures in a thread, as a run would, without any action.

    One search runs at a time. A new run, cancel and shutdown stop the search in progress, which ends once the
    detection it is running returns, its result dropped. A run asked meanwhile waits for it to end; only the last one
    asked waits. The result is read once finished is emitted.

    :param mouse_position: Mouse position of the driver, for a fixed position relative to the mouse.
    :param locate: Locates an element, as locate_element; imported in the thread by default, as it loads the OCR.
    """

    __test__ = False  # not a test class for pytest

    finished = Signal()
    """A search ended; see result."""
    running_changed = Signal()

    def __init__(self, mouse_position: tuple[int, int], parent: QObject | None = None, locate: Locate | None = None):
        super().__init__(parent)
        self._mouse_position = mouse_position
        self._locate = locate or _locate_element
        self._thread: _Search | None = None
        self._pending: _Search | None = None  # waits for the thread in progress, stopped, to end
        self.result: TestResult | None = None

    def is_running(self) -> bool:
        """A search runs or waits, its result to come."""
        return self._pending is not None or (self._thread is not None and not self._thread.is_stopped())

    def run(
        self,
        element: Element,
        captures: dict[int, np.ndarray],
        screens: list[Screen],
        scope: TestScope,
        variant: int | None,
        include_code: bool,
    ) -> None:
        """Searches a resolved element on captures; a search in progress is stopped first.

        :param element: Element as the Test searches it, see Store.tested_element.
        :param captures: Capture of each screen, by number.
        :param screens: Screens of the driver; empty for a single capture, as with VNC or a file.
        :param scope: Scope of the search, kept in the result with variant and include_code.
        """
        result = TestResult(scope, variant, None, dict(captures), include_code, element=element)
        search = _Search(self, self._locate, element, grabber(captures, screens), screens, self._mouse_position, result)
        search.done.connect(partial(self._done, search))
        if self._thread is None:
            self._start(search)
        else:
            self._thread.stop()
            self._forget_pending()
            self._pending = search
        self.running_changed.emit()

    def cancel(self) -> None:
        """Stops the search in progress and forgets the one waiting, if any."""
        if self.is_running():
            self._forget_pending()
            if self._thread is not None:
                self._thread.stop()
            self.running_changed.emit()

    def shutdown(self) -> None:
        """Stops the search in progress and waits for its thread to end."""
        self._forget_pending()
        if self._thread is not None:
            self._thread.stop()
            self._thread.wait()
            self._thread = None

    def _forget_pending(self) -> None:
        if self._pending is not None:
            self._pending.deleteLater()  # never started
            self._pending = None

    def _start(self, search: "_Search") -> None:
        self._thread = search
        search.start()

    def _done(self, search: "_Search") -> None:
        search.wait()
        if search is not self._thread:
            return  # ended as the runner shut down
        self._thread = None
        if self._pending is not None:
            pending, self._pending = self._pending, None
            self._start(pending)
        elif not search.is_stopped():
            self.result = search.result
            self.running_changed.emit()
            self.finished.emit()
        else:
            self.running_changed.emit()


class _Search(QThread):
    """Thread running one search; result is complete once done is emitted."""

    done = Signal()

    def __init__(
        self,
        runner: TestRunner,
        locate: Locate,
        element: Element,
        grab: Grab,
        screens: list[Screen],
        mouse_position: tuple[int, int],
        result: TestResult,
    ):
        super().__init__(runner)
        self._locate = locate
        self._element, self._grab, self._screens, self._mouse = element, grab, screens, mouse_position
        self._stop = threading.Event()
        self.result = result

    def stop(self) -> None:
        """Asks the search to end at its next step; its result is dropped."""
        self._stop.set()

    def is_stopped(self) -> bool:
        return self._stop.is_set()

    def run(self) -> None:
        start = time.perf_counter()
        try:
            report = self._locate(self._element, self._grab, self._screens, self._mouse, self._stop.is_set)
        except Exception as failure:  # noqa: BLE001 - any failure of the search is shown in the results
            message = str(failure) or type(failure).__name__
            self.result = _with(self.result, time.perf_counter() - start, error=message)
        else:
            used, error = used_match(report, self._element.match_index or 0)
            self.result = _with(self.result, time.perf_counter() - start, report=report, used=used, error=error)
        self.done.emit()


def _with(result: TestResult, duration: float, **fields) -> TestResult:
    return replace(result, duration=duration, **fields)


def _locate_element(
    element: Element, grab: Grab, screens: list[Screen], mouse: tuple[int, int], stopped: Stopped
) -> "LocateReport":
    """locate_element, imported on the first search: the detection loads the OCR."""
    from guimauve.detection.locate import locate_element

    return locate_element(element, grab, screens, mouse, stopped)
