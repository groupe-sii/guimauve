"""Windowing system the editor runs on."""

from enum import Enum

from PySide6.QtGui import QGuiApplication


class Platform(Enum):
    WINDOWS = "windows"
    X11 = "x11"
    WAYLAND = "wayland"
    OTHER = "other"
    """Offscreen, macOS or unknown: no native window to act on."""


def detect(qt_platform: str) -> Platform:
    """Platform matching a Qt platform plugin name, such as "windows", "xcb" or "wayland-egl"."""
    if qt_platform == "windows":
        return Platform.WINDOWS
    if qt_platform == "xcb":
        return Platform.X11
    if qt_platform.startswith("wayland"):
        return Platform.WAYLAND
    return Platform.OTHER


def current_platform() -> Platform:
    """Platform of the running QGuiApplication."""
    return detect(QGuiApplication.platformName())
