from abc import ABC, abstractmethod

import numpy

from guimauve.enums import Button, Key


class Driver(ABC):
    @abstractmethod
    def capture(self, area=None) -> numpy.ndarray:
        """Captures the current screen and returns an image object."""
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
