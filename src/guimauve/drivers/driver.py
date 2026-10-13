from abc import ABC, abstractmethod
from typing import NamedTuple

import numpy

from guimauve.enums import Button, Key
from guimauve.models.area import Area


class Screen(NamedTuple):
    """Position and size of a screen on the desktop; screens left of or above the primary one have negative offsets."""

    left: int
    top: int
    width: int
    height: int


class Driver(ABC):
    @abstractmethod
    def capture(self, screen: int, area: Area | None = None) -> numpy.ndarray:
        """Captures a screen, or an area of it.

        :param screen: 1 for the primary screen, n for screen n, 0 for all screens as one image.
        :param area: Area to capture, relative to the screen.
        :return: The captured image (RGB).
        """
        pass

    @abstractmethod
    def screens(self) -> list[Screen]:
        """Lists the screens.

        :return: The screens by number: 0 bounds all of them, 1 is the primary one, then the others from left to
            right and top to bottom. Empty when the driver cannot list the screens, as with VNC: screen numbers are
            then ignored.
        """
        pass

    @abstractmethod
    def key_down(self, key: Key):
        """Presses down the specified key."""
        pass

    @abstractmethod
    def key_up(self, key: Key):
        """Releases the specified key."""
        pass

    @abstractmethod
    def mouse_down(self, button: Button):
        """Presses down the specified mouse button."""
        pass

    @abstractmethod
    def mouse_up(self, button: Button):
        """Releases the specified mouse button."""
        pass

    @abstractmethod
    def mouse_move(self, x: int, y: int):
        """Moves the mouse to the specified (x, y) coordinates.

        :param x: The x-coordinate to move the mouse to.
        :param y: The y-coordinate to move the mouse to.
        """
        pass

    @abstractmethod
    def mouse_scroll(self, v: int, h: int):
        """Scrolls the mouse wheel.

        :param v: The vertical scroll amount.
        :param h: The horizontal scroll amount.
        """
        pass

    @abstractmethod
    def mouse_position(self) -> tuple[int, int]:
        """Returns the current mouse position as (x, y) coordinates."""
        pass

    @abstractmethod
    def paste(self, text: str):
        """Pastes the given text"""
        pass

    @abstractmethod
    def type(self, text: str):
        """Types the given text"""
        pass

    @abstractmethod
    def connect(self):
        """For remote drivers that require starting a session."""
        pass

    @abstractmethod
    def close(self):
        """For remote drivers that require closing a session."""
        pass
