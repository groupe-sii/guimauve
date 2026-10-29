"""Running the Test on a capture chosen for the session: the screens at opening, a new capture, or a file."""

import time

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QWidget

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.panels import image_files
from guimauve.gui.element_editor_next.panels.capture_flow import FAILED, NO_INITIAL, read_delay, write_delay
from guimauve.gui.element_editor_next.panels.wording import plural
from guimauve.gui.element_editor_next.services import Captures, CaptureService, CaptureSource, TestRunner, read_image
from guimauve.gui.element_editor_next.state import Mode, Severity, Store, TestScope

INITIAL = "Initial screen"
CAPTURED = "Captured {time}"
NO_CAPTURE = "No capture to test on: capture the screens first"
NO_VARIANT = "Select a variant to test it"
FIX = "Fix {issues} to test"


class TestFlow(QObject):
    """Chooses the capture of the Test and runs it there, as a run would search, without any action.

    The capture stays for the session: Run test never captures again. Initial screen, the default, uses the captures
    taken at opening. Instant and After a delay take new ones through the capture service, the window hidden during
    the delay; a file is a single screen, as with VNC. A new capture runs nothing: it makes the result stale until
    the next test. The result goes to the store. A request of the store, F5, runs the test in Test mode.

    :param runner: Searches the element in its thread.
    :param window: Window of the editor, hidden during a delay, parent of the file dialog.
    """

    __test__ = False  # not a test class for pytest

    changed = Signal()
    """The capture, its source, the error or whether a test runs changed."""

    def __init__(self, store: Store, service: CaptureService, runner: TestRunner, settings: QSettings, window: QWidget):
        super().__init__(window)
        self._store, self._service, self._runner = store, service, runner
        self._settings, self._window = settings, window
        self._captures: Captures = service.initial()
        self._screens: list[Screen] = store.screens
        self._label = INITIAL
        self._initial_error = None if self._captures else (service.error or NO_INITIAL)
        self._error: str | None = None
        self._waiting = False  # for the capture of the service

        service.captured.connect(self._captured)
        service.failed.connect(self._failed)
        service.capturing_changed.connect(self.changed)
        runner.running_changed.connect(self.changed)
        runner.finished.connect(self._finished)
        store.test_requested.connect(self.run)
        store.document_changed.connect(self.changed)  # errors and the selection decide whether a test can run
        store.selection_changed.connect(self.changed)
        store.mode_changed.connect(self.changed)

    # State

    @property
    def source(self) -> str:
        """What the capture is: Initial screen, the time of a capture, or the name of a file."""
        return self._label

    @property
    def initial_error(self) -> str | None:
        """Why there are no captures from the opening, or None."""
        return self._initial_error

    @property
    def error(self) -> str | None:
        """Message of the last capture that failed, until the next one or clear_error."""
        return self._error

    def clear_error(self) -> None:
        if self._error is not None:
            self._error = None
            self.changed.emit()

    @property
    def delay(self) -> int:
        return read_delay(self._settings)

    def set_delay(self, seconds: int) -> None:
        write_delay(self._settings, seconds)

    def is_running(self) -> bool:
        """A capture for the Test or a search is under way."""
        return self._waiting or self._runner.is_running()

    def is_capturing(self) -> bool:
        """The driver is taking the captures asked by the flow."""
        return self._waiting and self._service.is_capturing()

    def blocked(self) -> str | None:
        """Why the test cannot run now, or None."""
        store = self._store
        if not store.can_save:
            errors = sum(issue.severity is Severity.ERROR for issue in store.issues)
            return FIX.format(issues=plural(errors, "issue"))
        if store.test_scope is TestScope.VARIANT and store.selected_variant is None:
            return NO_VARIANT
        if not self._captures:
            return NO_CAPTURE
        return None

    # Actions

    def run(self) -> None:
        """Searches the element on the current capture, in Test mode, unless blocked or capturing."""
        store = self._store
        if store.mode is not Mode.TEST or self._waiting or self.blocked() is not None:
            return
        variant = store.selected_variant if store.test_scope is TestScope.VARIANT else None
        self._runner.run(
            store.tested_element(), self._captures, self._screens, store.test_scope, variant, store.include_code
        )

    def capture(self, source: CaptureSource) -> None:
        """Changes the capture of the Test; FILE asks for the file."""
        if self._waiting:
            return
        self.clear_error()
        if source is CaptureSource.INITIAL:
            if self._service.initial():
                self._use(self._service.initial(), self._store.screens, INITIAL)
        elif source is CaptureSource.FILE:
            self._import()
        else:
            self._runner.cancel()
            self._waiting = True
            if source is CaptureSource.DELAYED:
                self._window.hide()  # out of the way while the user prepares the screen
                self._service.capture_later(self.delay)
            else:
                self._service.capture_now()
            self.changed.emit()

    def cancel(self) -> None:
        """Stops the test or the capture under way, if any."""
        if self._waiting:
            self._waiting = False
            self._service.cancel()
            self._give_back()
        self._runner.cancel()
        self.changed.emit()

    # Steps

    def _use(self, captures: Captures, screens: list[Screen], label: str) -> None:
        self._captures, self._screens, self._label = captures, screens, label
        self._store.make_test_stale()
        self.changed.emit()

    def _captured(self) -> None:
        if self._waiting:
            self._waiting = False
            self._give_back()
            self._use(self._service.last(), self._store.screens, CAPTURED.format(time=time.strftime("%H:%M:%S")))

    def _failed(self) -> None:
        if self._waiting:
            self._waiting = False
            self._error = FAILED.format(error=self._service.error)
            self._give_back()
            self.changed.emit()

    def _finished(self) -> None:
        self._store.set_test_result(self._runner.result)

    def _give_back(self) -> None:
        """Shows the window again if a delayed capture hid it, and gives it the focus."""
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _import(self) -> None:
        path = image_files.ask_image_file(self._window)
        if path is None:
            return
        image = read_image(path)
        if image is None:
            image_files.warn(self._window, image_files.UNREADABLE)
            return
        self._use({1: image}, [], path.name)
