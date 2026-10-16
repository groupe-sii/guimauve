import platform

_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
_PROCESS_PER_MONITOR_DPI_AWARE = 2
_MONITOR_DEFAULTTOPRIMARY = 1
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


def get_primary_scaling() -> int:
    """Returns the display scaling of the primary monitor, in percent (100, 125, 150...).

    Windows only. Relies on the per-monitor DPI awareness set by `set_dpi_awareness`:
    without it, Windows would always report the default 96 DPI (100%).
    """
    if platform.system() != "Windows":
        raise NotImplementedError("Display scaling is only available on Windows")

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user32.MonitorFromPoint.restype = ctypes.c_void_p
    monitor = user32.MonitorFromPoint(wintypes.POINT(0, 0), _MONITOR_DEFAULTTOPRIMARY)

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
