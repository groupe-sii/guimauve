import platform

_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
_PROCESS_PER_MONITOR_DPI_AWARE = 2
_MONITOR_DEFAULTTONEAREST = 2
_MDT_EFFECTIVE_DPI = 0
_DEFAULT_DPI = 96


def set_dpi_awareness() -> None:
    """Make the process per-monitor DPI aware so all coordinates are physical pixels.

    Must run before pynput, mss or Qt touch the screen. Only the first call in a
    process takes effect; later calls fail silently. No-op on non-Windows platforms.
    """
    if platform.system() != "Windows":
        return

    import ctypes

    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        if user32.SetProcessDpiAwarenessContext(_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            return
    except AttributeError:
        pass  # Windows < 10 1703

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(_PROCESS_PER_MONITOR_DPI_AWARE)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()  # Windows < 8.1


def get_scaling(screen: int = 1) -> int:
    """Returns the display scaling of a screen, in percent (100, 125, 150...).

    Windows only. Relies on the per-monitor DPI awareness set by `set_dpi_awareness`:
    without it, Windows would always report the default 96 DPI (100%).

    :param screen: Screen number, as numbered by the local driver: 1 is the primary screen.
    :raises ValueError: If the screen does not exist.
    """
    if platform.system() != "Windows":
        raise NotImplementedError("Display scaling is only available on Windows")

    import ctypes
    from ctypes import wintypes

    from mss import mss

    from guimauve.drivers.local.driver import _number_screens

    with mss() as sct:
        screens = _number_screens(sct.monitors)
    if not 1 <= screen < len(screens):
        raise ValueError(f"Screen {screen} does not exist: {len(screens) - 1} screens available")
    rect = screens[screen]

    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    center = wintypes.POINT(rect.left + rect.width // 2, rect.top + rect.height // 2)
    monitor = user32.MonitorFromPoint(center, _MONITOR_DEFAULTTONEAREST)

    dpi_x, dpi_y = ctypes.c_uint(), ctypes.c_uint()
    shcore = ctypes.windll.shcore
    shcore.GetDpiForMonitor.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
    ]
    if shcore.GetDpiForMonitor(monitor, _MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) != 0:
        raise OSError("GetDpiForMonitor failed")

    return round(dpi_x.value * 100 / _DEFAULT_DPI)


def get_screen_size() -> tuple[int, int]:
    system = platform.system()
    if system == "Windows":
        return _get_screen_size_windows()
    if system == "Linux":
        return _get_screen_size_linux()
    raise NotImplementedError(f"Unsupported platform: {system}")


def _get_screen_size_windows() -> tuple[int, int]:
    import ctypes

    user32 = ctypes.windll.user32
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    return width, height


def _get_screen_size_linux() -> tuple[int, int]:
    raise NotImplementedError("Linux screen size detection not implemented yet")
