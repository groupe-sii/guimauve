"""Selection of an area or a point on the frozen captures of all the screens."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QCursor, QGuiApplication

from guimauve.gui.element_editor_next.canvas.region import Region
from guimauve.gui.element_editor_next.overlays.geometry import fit_capture
from guimauve.gui.element_editor_next.overlays.selection import SelectionMode, SelectionOverlay
from guimauve.gui.element_editor_next.services.capture import Captures
from guimauve.gui.element_editor_next.services.images import to_qimage
from guimauve.gui.element_editor_next.system import ScreenMap

WINDOW_FLAGS = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool


@dataclass(frozen=True)
class Selection:
    """What was selected, in pixels of the capture of a screen: physical, relative to that screen.

    :param screen: Number of the screen in the driver.
    :param area: Rectangle selected in the AREA mode.
    :param point: Pixel selected in the POINT mode.
    """

    screen: int
    area: Region | None = None
    point: tuple[int, int] | None = None


class SelectionSession(QObject):
    """One window per screen on its frozen capture; finished once an area or a point is selected, or on Esc.

    Each window covers its Qt screen; a remote screen, or one Qt does not show, is fitted on the primary screen with
    its scale in the banner. With several screens, each shows its number until a drag starts. A selection stays in
    the screen where it started.

    :param captures: Capture of each screen, by number, as CaptureService gives them.
    :param title: What to do, in the banner of every screen.
    """

    finished = Signal()
    """The selection ended; result is None when cancelled."""

    def __init__(
        self,
        captures: Captures,
        screens: ScreenMap,
        mode: SelectionMode,
        title: str | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._mode = mode
        self.result: Selection | None = None
        self.overlays: dict[int, SelectionOverlay] = {}
        for number, capture in captures.items():
            image = to_qimage(capture)
            screen = screens.qt_screen(number)
            note = None
            target = screen or QGuiApplication.primaryScreen()
            shown = None
            if screen is None:  # remote, or not shown by Qt: fitted on the primary screen
                area = QRectF(0, 0, target.geometry().width(), target.geometry().height())
                shown = fit_capture(image.width(), image.height(), area)
                note = f"Remote screen at {round(100 * shown.width() / image.width())} %"
            overlay = SelectionOverlay(image, mode, shown, note, title)
            overlay.setWindowFlags(WINDOW_FLAGS)
            overlay.setScreen(target)
            overlay.setGeometry(target.geometry())
            overlay.selected.connect(lambda number=number: self._select(number))
            overlay.cancelled.connect(self.cancel)
            overlay.drag_started.connect(self._hide_numbers)
            self.overlays[number] = overlay
        if len(self.overlays) > 1:
            for number, overlay in self.overlays.items():
                overlay.show_number(number)

    def start(self) -> None:
        """Shows the windows; the one under the cursor takes the focus, for Esc."""
        for overlay in self.overlays.values():
            overlay.show()
        under = QGuiApplication.screenAt(QCursor.pos())
        focused = next((o for o in self.overlays.values() if o.screen() is under), None)
        focused = focused or next(iter(self.overlays.values()), None)
        if focused is not None:
            focused.raise_()
            focused.activateWindow()
            focused.setFocus(Qt.FocusReason.OtherFocusReason)

    def _select(self, number: int) -> None:
        overlay = self.overlays[number]
        if self._mode is SelectionMode.AREA:
            self.result = Selection(number, area=overlay.region())
        else:
            self.result = Selection(number, point=overlay.point())
        self._close()

    def cancel(self) -> None:
        """Ends the selection without result, e.g. when the editor closes meanwhile."""
        if self.overlays:
            self.result = None
            self._close()

    def _hide_numbers(self) -> None:
        for overlay in self.overlays.values():
            overlay.hide_number()

    def _close(self) -> None:
        for overlay in self.overlays.values():
            overlay.close()
            overlay.deleteLater()
        self.overlays = {}
        self.finished.emit()
