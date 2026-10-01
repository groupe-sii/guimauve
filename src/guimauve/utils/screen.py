import platform

_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
_PROCESS_PER_MONITOR_DPI_AWARE = 2


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
