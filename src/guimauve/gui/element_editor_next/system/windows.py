"""Win32 calls through ctypes; each one returns False when the system does not support it."""

import sys

_WDA_NONE = 0x00000000
_WDA_EXCLUDEFROMCAPTURE = 0x00000011
_MIN_BUILD = 19041
"""Windows 10 version 2004, the first one with WDA_EXCLUDEFROMCAPTURE."""


def set_excluded_from_capture(hwnd: int, excluded: bool) -> bool:
    """Removes the window from screen captures while keeping it visible on screen, or puts it back."""
    if sys.platform != "win32":
        return False
    if sys.getwindowsversion().build < _MIN_BUILD:
        return False

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
    return bool(user32.SetWindowDisplayAffinity(hwnd, _WDA_EXCLUDEFROMCAPTURE if excluded else _WDA_NONE))
