"""Searching the element of the Test mode on captures already taken, in a thread, without any action."""

import threading
import time
from collections.abc import Callable
from dataclasses import replace
from functools import partial

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from guimauve.detection.report import LocateReport
from guimauve.detection.worker import Grab, grabber
from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.services.search_process import SearchProcess
from guimauve.gui.element_editor_next.state import TestResult, TestScope
from guimauve.models.element import Element

Stopped = Callable[[], bool]
Locate = Callable[[Element, Grab, list[Screen], tuple[int, int], Stopped], LocateReport]
Captures = dict[int, np.ndarray]
Searcher = Callable[[Element, Captures, list[Screen], tuple[int, int], Stopped], tuple[LocateReport, float]]
"""Searches an element on captures; gives the report and the seconds the search took."""


def used_match(report: LocateReport, index: int) -> tuple[int | None, str | None]:
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

    The search runs in a process of its own, so that a long detection, such as the OCR, never holds the Python of
    the window; the thread only waits for it. One search runs at a time. A new run, cancel and shutdown stop the
    search in progress, which ends once the detection it is running returns, its result dropped. A run asked
    meanwhile waits for it to end; only the last one asked waits. The result is read once finished is emitted.

    :param mouse_position: Mouse position of the driver, for a fixed position relative to the mouse.
    :param locate: Locates an element in the thread instead, as locate_element, for the tests.
    :param process: Process of the searches; a new one by default, started at the first search or by prepare.
    """

    __test__ = False  # not a test class for pytest

    finished = Signal()
    """A search ended; see result."""
    running_changed = Signal()

    def __init__(
        self,
        mouse_position: tuple[int, int],
        parent: QObject | None = None,
        locate: Locate | None = None,
        process: SearchProcess | None = None,
    ):
        super().__init__(parent)
        self._mouse_position = mouse_position
        self._process: SearchProcess | None = None
        if locate is not None:
            self._search: Searcher = _in_thread(locate)
        else:
            self._process = process or SearchProcess()
            self._search = _in_process(self._process)
        self._thread: _Search | None = None
        self._pending: _Search | None = None  # waits for the thread in progress, stopped, to end
        self.result: TestResult | None = None

    def prepare(self) -> None:
        """Starts the process of the searches in the background, so that the first test does not wait for it."""
        process = self._process
        if process is not None:
            threading.Thread(target=_start_quietly, args=(process,), daemon=True).start()

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
        search = _Search(self, self._search, element, captures, screens, self._mouse_position, result)
        search.stopping.connect(self._stop_process)
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
        """Stops the search in progress, waits for its thread to end, and ends the process."""
        self._forget_pending()
        if self._thread is not None:
            self._thread.stop()
            self._thread.wait()
            self._thread = None
        if self._process is not None:
            self._process.close()

    def _stop_process(self) -> None:
        if self._process is not None:
            self._process.stop()

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
    stopping = Signal()
    """stop was called: the process, if any, must stop its search."""

    def __init__(
        self,
        runner: TestRunner,
        search: Searcher,
        element: Element,
        captures: Captures,
        screens: list[Screen],
        mouse_position: tuple[int, int],
        result: TestResult,
    ):
        super().__init__(runner)
        self._search = search
        self._element, self._captures, self._screens, self._mouse = element, captures, screens, mouse_position
        self._stop = threading.Event()
        self.result = result

    def stop(self) -> None:
        """Asks the search to end at its next step; its result is dropped."""
        if not self._stop.is_set():
            self._stop.set()
            self.stopping.emit()

    def is_stopped(self) -> bool:
        return self._stop.is_set()

    def run(self) -> None:
        try:
            report, duration = self._search(
                self._element, self._captures, self._screens, self._mouse, self._stop.is_set
            )
        except Exception as failure:  # noqa: BLE001 - any failure of the search is shown in the results
            self.result = replace(self.result, error=str(failure) or type(failure).__name__)
        else:
            used, error = used_match(report, self._element.match_index or 0)
            self.result = replace(self.result, duration=duration, report=report, used=used, error=error)
        self.done.emit()


def _in_thread(locate: Locate) -> Searcher:
    def search(
        element: Element, captures: Captures, screens: list[Screen], mouse: tuple[int, int], stopped: Stopped
    ) -> tuple[LocateReport, float]:
        start = time.perf_counter()
        report = locate(element, grabber(captures, screens), screens, mouse, stopped)
        return report, time.perf_counter() - start

    return search


def _in_process(process: SearchProcess) -> Searcher:
    def search(
        element: Element, captures: Captures, screens: list[Screen], mouse: tuple[int, int], stopped: Stopped
    ) -> tuple[LocateReport, float]:
        return process.search(element, captures, screens, mouse)  # stopped through stop, from the runner

    return search


def _start_quietly(process: SearchProcess) -> None:
    try:
        process.start()
    except Exception:  # noqa: BLE001 - the first search tells the error
        pass
