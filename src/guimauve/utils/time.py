import time
from typing import Union


def sleep(seconds: Union[float, int]) -> None:
    """
    Sleep for a specified number of seconds.

    :param seconds: The number of seconds to sleep.
    """
    if seconds == 0:
        return

    if seconds < 0:
        raise ValueError("Sleep duration must be non-negative")

    busy_wait_threshold = 0.015
    if seconds >= busy_wait_threshold:
        time.sleep(seconds)
        return

    start_time = time.perf_counter()
    while time.perf_counter() - start_time < seconds:
        pass
