"""Taking the image of a variant: from a capture and an area selected on it, or from a file."""

from collections.abc import Callable

import numpy as np
from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.overlays import SelectionMode, SelectionSession
from guimauve.gui.element_editor_next.panels import image_files
from guimauve.gui.element_editor_next.services import Captures, CaptureService, CaptureSource, read_image
from guimauve.gui.element_editor_next.state import Store, new_name
from guimauve.models.variant import ImageVariant

DELAY_KEY = "capture/delay"
DEFAULT_DELAY = 3
DELAYS = (1, 3, 5, 10)
MAX_DELAY = 60
NO_INITIAL = "The screens could not be captured at opening"
FAILED = "Capture failed: {error}"
SELECT = "Select the area to capture"

SessionFactory = Callable[[Captures], SelectionSession]
NEW = None
"""Variant to take the image for: a new one, added once the image is taken."""


class CaptureFlow(QObject):
    """Takes an image, then replaces the image of a variant, its targets kept, or adds a new image variant.

    A capture is followed by the selection of an area on the frozen screens, in one screen; a cancelled selection
    changes nothing. For a delayed capture, the window hides at once, leaving the screen to prepare, and shows again
    once the selection ends or the capture fails; the delay chosen is kept for the next sessions. The focus goes back
    to the window afterwards. Shared by the canvas and the variant list.

    :param window: Window of the editor, parent of the dialogs and given back the focus.
    :param session: Builds the selection on some captures; the one of all the screens by default.
    """

    changed = Signal()
    """A capture started or ended, or the error changed."""

    def __init__(
        self,
        store: Store,
        service: CaptureService,
        settings: QSettings,
        window: QWidget,
        session: SessionFactory | None = None,
    ):
        super().__init__(window)
        self._store, self._service, self._settings, self._window = store, service, settings, window
        self._make_session = session or (
            lambda captures: SelectionSession(captures, service.screens, SelectionMode.AREA, SELECT)
        )
        self._initial_error = None if service.initial() else (service.error or NO_INITIAL)
        self._error: str | None = None
        self._waiting = False  # for the capture of the service
        self._target: int | None = NEW
        self._session: SelectionSession | None = None
        service.captured.connect(self._captured)
        service.failed.connect(self._failed)
        service.capturing_changed.connect(self.changed)

    # State

    @property
    def delay(self) -> int:
        value = self._settings.value(DELAY_KEY, DEFAULT_DELAY)
        try:
            return min(max(int(str(value)), 1), MAX_DELAY)
        except (TypeError, ValueError):
            return DEFAULT_DELAY

    def set_delay(self, seconds: int) -> None:
        self._settings.setValue(DELAY_KEY, min(max(seconds, 1), MAX_DELAY))

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
    def is_remote(self) -> bool:
        """The captures come from a remote screen, through VNC."""
        return self._service.screens.is_remote

    def is_capturing(self) -> bool:
        """The driver is taking the captures asked by the flow."""
        return self._waiting and self._service.is_capturing()

    def is_busy(self) -> bool:
        """A capture is waiting for its delay or the driver, or an area is being selected."""
        return self._waiting or self._session is not None

    # Actions

    def capture(self, source: CaptureSource, variant: int | None = NEW) -> None:
        """Takes the image of a variant, a new one by default, from a source; FILE asks for the file."""
        if self.is_busy():
            return
        self._target = variant
        self.clear_error()
        if source is CaptureSource.FILE:
            self._import()
        elif source is CaptureSource.INITIAL:
            if self._service.initial():
                self._select(self._service.initial())
        else:
            self._waiting = True
            if source is CaptureSource.DELAYED:
                self._window.hide()  # out of the way while the user prepares the screen
                self._service.capture_later(self.delay)
            else:
                self._service.capture_now()
        self.changed.emit()

    def cancel(self) -> None:
        """Stops a delayed capture, or closes the selection in progress, without taking an image."""
        if self._waiting:
            self._waiting = False
            self._service.cancel()
            self._give_back()
        if self._session is not None:
            self._session.cancel()
        self.changed.emit()

    # Steps

    def _captured(self) -> None:
        if self._waiting:
            self._waiting = False
            self._select(self._service.last())
            self.changed.emit()

    def _failed(self) -> None:
        if self._waiting:
            self._waiting = False
            self._error = FAILED.format(error=self._service.error)
            self._give_back()
            self.changed.emit()

    def _select(self, captures: Captures) -> None:
        session = self._make_session(captures)
        self._session = session
        session.finished.connect(lambda: self._selected(session, captures))
        session.start()

    def _selected(self, session: SelectionSession, captures: Captures) -> None:
        self._session = None
        selection = session.result
        if selection is not None and selection.area is not None:
            area = selection.area
            image = captures[selection.screen][area.top : area.bottom, area.left : area.right].copy()
            self._take(image)
        self._give_back()
        self.changed.emit()

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
        self._take(image)

    def _take(self, image: np.ndarray) -> None:
        store, target = self._store, self._target
        if target is NEW:
            names = [variant.name for variant in store.document.variants]
            store.add_variant(ImageVariant(name=new_name(names), image=image))
        elif target in store.variant_keys():  # not deleted meanwhile
            store.replace_image(target, image)
