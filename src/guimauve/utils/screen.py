import platform


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
    user32.SetProcessDPIAware()
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    return width, height


def _get_screen_size_linux() -> tuple[int, int]:
    raise NotImplementedError("Linux screen size detection not implemented yet")
