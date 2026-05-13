import time


def sleep(seconds):
    """
    Sleep for a specified number of seconds.

    :param seconds: The number of seconds to sleep.
    :type seconds: float | int
    """
    if seconds == 0:
        return

    if seconds < 0:
        raise ValueError("Sleep duration must be non-negative")

    start_time = time.perf_counter()
    while time.perf_counter() - start_time < seconds:
        pass
