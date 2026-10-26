"""Picking a point or drawing an area on the screens captured at opening, for the fixed position and the search
area."""

from collections.abc import Callable, Sequence
from typing import Any

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.overlays import Selection, SelectionMode, SelectionSession
from guimauve.gui.element_editor_next.panels.capture_flow import NO_INITIAL
from guimauve.gui.element_editor_next.services import Captures, CaptureService
from guimauve.gui.element_editor_next.system import ScreenMap
from guimauve.models.area import Area

SessionFactory = Callable[[Captures, SelectionMode], SelectionSession]
TITLES = {SelectionMode.POINT: "Pick the click point", SelectionMode.AREA: "Draw the search area"}


def screens_offered(screen: Any, mode: SelectionMode, numbers: Sequence[int]) -> list[int]:
    """Screens where a value of the element applies, among those captured: those to show for the selection.

    No screen is the primary one, 0 all of them; a list gives its first screen to a point, which is clicked on one
    screen, and all its screens to an area, which applies to each.
    """
    if screen == 0:
        wanted = list(numbers)
    elif isinstance(screen, list):
        wanted = screen[:1] if mode is SelectionMode.POINT else screen
    else:
        wanted = [1 if screen is None else screen]
    return [number for number in wanted if number in numbers] or list(numbers[:1])


def offset(selection: Selection, screen: Any, screens: ScreenMap) -> tuple[int, int]:
    """What to add to a selection, relative to its screen, to make it relative to what the value applies to.

    With screen 0, a point is relative to the primary screen, so it can be negative, and an area to the image of the
    whole desktop, which starts at the top left of all the screens. Otherwise, or without the screens of the driver,
    nothing.
    """
    picked, desktop, primary = screens.driver_screen(selection.screen), screens.desktop(), screens.driver_screen(1)
    if screen != 0 or picked is None or desktop is None or primary is None:
        return 0, 0
    origin = primary if selection.point is not None else desktop
    return picked.left - origin.left, picked.top - origin.top


class ScreenPicker(QObject):
    """Opens the selection on the captures taken at opening, then gives what was picked in the coordinates of the
    value: a point (x, y) for the fixed position, an Area for the search area; nothing when cancelled.

    :param window: Window of the editor, given back the focus afterwards.
    :param session: Builds the selection; the one of all the screens by default.
    """

    def __init__(self, service: CaptureService, window: QWidget, session: SessionFactory | None = None):
        super().__init__(window)
        self._service, self._window = service, window
        self._make_session = session or (
            lambda captures, mode: SelectionSession(captures, service.screens, mode, TITLES[mode])
        )
        self._session: SelectionSession | None = None

    @property
    def unavailable(self) -> str | None:
        """Why nothing can be picked, the screens not captured at opening; None when it can."""
        return None if self._service.initial() else (self._service.error or NO_INITIAL)

    def pick_point(self, screen: Any, done: Callable[[int, int], None]) -> None:
        """Lets the user click a point on the screens of the value of screen; done gets its coordinates."""

        def picked(selection: Selection) -> None:
            if selection.point is not None:
                dx, dy = offset(selection, screen, self._service.screens)
                done(selection.point[0] + dx, selection.point[1] + dy)

        self._open(SelectionMode.POINT, screen, picked)

    def pick_area(self, screen: Any, done: Callable[[Area], None]) -> None:
        """Lets the user draw an area on the screens of the value of screen; done gets it."""

        def picked(selection: Selection) -> None:
            if selection.area is not None:
                dx, dy = offset(selection, screen, self._service.screens)
                area = selection.area
                done(Area(left=area.left + dx, top=area.top + dy, right=area.right + dx, bottom=area.bottom + dy))

        self._open(SelectionMode.AREA, screen, picked)

    def _open(self, mode: SelectionMode, screen: Any, picked: Callable[[Selection], None]) -> None:
        initial = self._service.initial()
        if self._session is not None or not initial:
            return
        shown = screens_offered(screen, mode, sorted(initial))
        session = self._make_session({number: initial[number] for number in shown}, mode)
        self._session = session

        def finished() -> None:
            self._session = None
            if session.result is not None:
                picked(session.result)
            self._window.raise_()
            self._window.activateWindow()

        session.finished.connect(finished)
        session.start()
