"""Process that runs the searches of the Test, so that the OCR never holds the Python of the window."""

import os
import secrets
import subprocess
import sys
import threading
from multiprocessing.connection import Client, Connection

import numpy as np

from guimauve.detection.report import LocateReport
from guimauve.detection.worker import DEFAULT_LOCATE
from guimauve.drivers.driver import Screen
from guimauve.models.element import Element

QUIT_TIMEOUT = 2.0
"""Seconds the process has to end on its own before it is killed."""
LOST = "The search process stopped unexpectedly"


class SearchProcess:
    """One process for the searches of a session, started when first needed and kept with the detection loaded.

    A search blocks the calling thread, which waits without holding Python. stop, from any thread, asks the search
    in progress to end at its next step. If the process dies, the search fails and the next one starts another.

    :param locate: Function searching, as ``module:function``; locate_element by default.
    :param python_path: Directories the process can import from, besides those of this one.
    """

    def __init__(self, locate: str = DEFAULT_LOCATE, python_path: list[str] | None = None):
        self._locate = locate
        self._python_path = python_path or []
        self._lock = threading.Lock()
        self._sending = threading.Lock()  # a stop may come from another thread while a search is sent
        self._process: subprocess.Popen[str] | None = None
        self._connection: Connection | None = None
        self._closed = False  # by close: a start still on its way must not leave a process behind

    def start(self) -> None:
        """Starts the process if it does not run; blocks until it listens.

        :raises RuntimeError: If the process cannot start, or close was called.
        """
        with self._lock:
            if self._closed:
                raise RuntimeError(LOST)
            if self._process is not None and self._process.poll() is None and self._connection is not None:
                return
            self._close()
            key = secrets.token_bytes(32)
            env = dict(os.environ)
            env["PYTHONPATH"] = os.pathsep.join([*self._python_path, *sys.path, env.get("PYTHONPATH", "")])
            process = subprocess.Popen(
                [sys.executable, "-m", "guimauve.detection.worker", self._locate],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(key.hex() + "\n")
            process.stdin.close()
            port = process.stdout.readline().strip()  # empty if the process ended
            process.stdout.close()
            if not port:
                process.wait()
                raise RuntimeError(LOST)
            self._process = process
            self._connection = Client(("127.0.0.1", int(port)), authkey=key)

    def search(
        self, element: Element, captures: dict[int, np.ndarray], screens: list[Screen], mouse: tuple[int, int]
    ) -> tuple[LocateReport, float]:
        """Searches a resolved element on captures, as locate_element does.

        :return: The report and the seconds the search took in the process.
        :raises RuntimeError: With the message of the search when it failed, or when the process stopped.
        """
        self.start()
        connection = self._connection
        assert connection is not None
        try:
            with self._sending:
                connection.send(("search", element, captures, screens, mouse))
            answer = connection.recv()
        except (EOFError, OSError) as error:
            self._lost()
            raise RuntimeError(LOST) from error
        if answer[0] == "error":
            raise RuntimeError(answer[1])
        return answer[1], answer[2]

    def stop(self) -> None:
        """Asks the search in progress, if any, to end at its next step."""
        connection = self._connection
        if connection is not None:
            try:
                with self._sending:
                    connection.send(("stop",))
            except (EOFError, OSError):
                pass

    def close(self) -> None:
        """Ends the process, killing it if it does not end in time; no other starts afterwards."""
        self._closed = True
        with self._lock:
            self._close()

    def _close(self) -> None:
        connection, process = self._connection, self._process
        self._connection = self._process = None
        if connection is not None:
            try:
                with self._sending:
                    connection.send(("quit",))
            except (EOFError, OSError):
                pass
            connection.close()
        if process is not None and process.poll() is None:
            try:
                process.wait(QUIT_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def _lost(self) -> None:
        with self._lock:
            self._close()
