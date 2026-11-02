"""Screens of the driver, in physical pixels, matched with the screens of Qt, in logical pixels.

Under Windows and X11, Qt keeps the native origin of each screen and divides its size by its pixel ratio: within a
screen, a logical point is the origin plus the physical offset divided by the ratio. The driver numbers its screens
as Driver.screens(): 0 bounds them all, 1 is the primary one, then the others.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QPointF
from PySide6.QtGui import QGuiApplication, QScreen

from guimauve.drivers.driver import Screen


@dataclass(frozen=True)
class ScreenGeometry:
    """A Qt screen as matched: native origin, logical size and pixel ratio."""

    x: int
    y: int
    width: int
    height: int
    ratio: float

    @property
    def physical_size(self) -> tuple[int, int]:
        return round(self.width * self.ratio), round(self.height * self.ratio)

    @staticmethod
    def of(screen: QScreen) -> "ScreenGeometry":
        rect = screen.geometry()
        return ScreenGeometry(rect.x(), rect.y(), rect.width(), rect.height(), screen.devicePixelRatio())


def match_screens(driver: Sequence[Screen], qt: Sequence[ScreenGeometry]) -> dict[int, int]:
    """Index of the Qt screen showing each screen of the driver, by number from 1.

    A Qt screen matches by its origin and physical size, else by its origin alone; the screens left are paired in
    the order of their positions, left to right then top to bottom, which may be wrong where Qt scales the origins
    (macOS, Wayland). Screens left without partner are missing from the result.
    """
    numbered = list(enumerate(driver))[1:]
    matches: dict[int, int] = {}
    free = list(range(len(qt)))

    def pair(same) -> None:
        for number, screen in numbered:
            if number in matches:
                continue
            index = next((i for i in free if same(screen, qt[i])), None)
            if index is not None:
                matches[number] = index
                free.remove(index)

    pair(lambda s, g: (g.x, g.y) == (s.left, s.top) and g.physical_size == (s.width, s.height))
    pair(lambda s, g: (g.x, g.y) == (s.left, s.top))
    left = sorted((number for number, _ in numbered if number not in matches), key=lambda n: driver[n][:2])
    for number, index in zip(left, sorted(free, key=lambda i: (qt[i].x, qt[i].y)), strict=False):
        matches[number] = index
    return matches


def to_logical(geometry: ScreenGeometry, point: QPointF) -> QPointF:
    """Point of a screen in physical pixels from its top left, as a global logical point of Qt."""
    return QPointF(geometry.x + point.x() / geometry.ratio, geometry.y + point.y() / geometry.ratio)


def to_physical(geometry: ScreenGeometry, point: QPointF) -> QPointF:
    """Global logical point of Qt, as a point of the screen in physical pixels from its top left."""
    return QPointF((point.x() - geometry.x) * geometry.ratio, (point.y() - geometry.y) * geometry.ratio)


class ScreenMap:
    """Screens of the driver with their Qt screens.

    Without screens from the driver, as with VNC, there is one screen, the remote one, shown on no Qt screen. The
    screens of the application are read again at each use: Qt replaces them when the displays change, e.g. when a
    driver changes the DPI awareness of the process.

    :param screens: Screens of the driver, as Driver.screens(); empty when unknown.
    :param qt_screens: Screens of Qt, those of the application at each use by default.
    """

    def __init__(self, screens: Sequence[Screen], qt_screens: Sequence[QScreen] | None = None):
        self._screens = list(screens)
        self._fixed = None if qt_screens is None else list(qt_screens)

    @property
    def is_remote(self) -> bool:
        """The driver gave no screens: one remote screen, matched with none of Qt."""
        return not self._screens

    def numbers(self) -> list[int]:
        """Numbers of the screens to capture one by one: 1 to n, or 1 alone for a remote screen."""
        return list(range(1, len(self._screens))) or [1]

    def desktop(self) -> Screen | None:
        """Bounds of all the screens, the screen 0 of the driver; None when remote."""
        return self._screens[0] if self._screens else None

    def driver_screen(self, number: int) -> Screen | None:
        return self._screens[number] if 0 < number < len(self._screens) else None

    def qt_screen(self, number: int) -> QScreen | None:
        """Qt screen showing a screen of the driver; None when remote or unmatched."""
        qt = list(QGuiApplication.screens()) if self._fixed is None else self._fixed
        index = match_screens(self._screens, [ScreenGeometry.of(screen) for screen in qt]).get(number)
        return None if index is None else qt[index]

    def to_logical(self, number: int, point: QPointF) -> QPointF | None:
        """Physical point of a screen of the driver as a global logical point; None without its Qt screen."""
        screen = self.qt_screen(number)
        return None if screen is None else to_logical(ScreenGeometry.of(screen), point)

    def to_physical(self, number: int, point: QPointF) -> QPointF | None:
        """Global logical point as a physical point of a screen of the driver; None without its Qt screen."""
        screen = self.qt_screen(number)
        return None if screen is None else to_physical(ScreenGeometry.of(screen), point)
