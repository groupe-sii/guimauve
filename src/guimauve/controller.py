import importlib
import logging
import math
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, TypeAlias

import cv2 as cv
import numpy as np

from guimauve.checks import (
    EnvironmentCheckError,
    check_dataset,
    check_scaling,
    check_screen_exists,
    check_screen_size,
    selected_datasets,
)
from guimauve.detection.detector import Match, Point
from guimauve.detection.locate import (
    LocateReport,
    crop_screen,
    locate_element,
    screen_at,
    screen_origin,
    to_area,
)
from guimauve.detection.locate import locate_text as locate_text_on_screens
from guimauve.detection.ocr import Ocr
from guimauve.drivers.driver import Driver
from guimauve.drivers.pausable_driver import PausableDriver
from guimauve.drivers.vnc.driver import VNCDriver
from guimauve.enums import Button, Key, Menu, MouseDirection, OcrFidelity, ScreenArea
from guimauve.gui import legacy_editor_enabled
from guimauve.gui.element_editor import EditorResult, ResumeMode
from guimauve.log import fields, mask
from guimauve.log_screenshot import log_screenshot
from guimauve.models.area import Area
from guimauve.models.data import Data
from guimauve.models.element import Element
from guimauve.models.model import ModelError
from guimauve.models.parameters import Parameters, ScreenCheck
from guimauve.models.replay import Replay
from guimauve.pause_manager import PauseManager
from guimauve.recorder.player import Player
from guimauve.storage.save import save_element
from guimauve.storage.sync import sync_dataset
from guimauve.storage.workspace import DataWorkspace
from guimauve.utils.image import diff_area, similarity_index
from guimauve.utils.time import sleep as sleep_

logger = logging.getLogger(__name__)
detection_logger = logging.getLogger("guimauve.detection.locate")
"""Logger of the detection, for what only the controller knows about it."""

DataType: TypeAlias = Data | Path | dict | str | None
ParametersType: TypeAlias = Parameters | Path | dict | str | None
SleepType: TypeAlias = int | float | None
Elements: TypeAlias = Element | Iterable[Element] | None

POLL_INTERVAL = 0.05


def _local_driver() -> Driver:
    # Imported on use: pynput needs a display, which a Linux server driving a VNC session has not
    from guimauve.drivers.local.driver import LocalDriver

    return LocalDriver()


DRIVERS: dict[str, Callable[..., Driver]] = {"local": _local_driver, "vnc": VNCDriver}


def get_elements_kwargs(kwargs: dict) -> dict[str, Sequence[Element]]:
    elements: dict[str, Sequence[Element]] = {}
    for param in ("element", "on", "off"):
        if param in kwargs:
            elements_value = kwargs[param]
            elements[param] = elements_value if isinstance(elements_value, (tuple, list)) else [elements_value]

    return elements


def handle_action(update_element: bool = True, use_wait: bool = True, sleep_after: bool = True):
    """Performs actions before and after the decorated method execution.

    :param update_element: If True, updates the element with default element parameters before executing action.
    :param use_wait: If True, use the wait method to ensure the element is present before executing action.
    :param sleep_after: If True, sleeps for a defined duration after executing action.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            with self._acting(func.__name__) as level:
                start = time.perf_counter()
                elements_params = get_elements_kwargs(kwargs)

                for param_name, element_list in elements_params.items():
                    updated_list = []
                    for element in element_list:
                        if not (element := self._prepare_element(element, update=update_element, wait=use_wait)):
                            logger.log(
                                level,
                                "%s skipped: %s was not edited",
                                func.__name__,
                                element_list[len(updated_list)].name,
                                extra=fields(action=func.__name__, success=False),
                            )
                            return None
                        updated_list.append(element)

                    if isinstance(kwargs[param_name], (list, tuple)):
                        kwargs[param_name] = updated_list
                    else:
                        kwargs[param_name] = updated_list[0]

                result = func(self, *args, **kwargs)

                if sleep_after:
                    delay = self.parameters.sleep
                    if kwargs.get("sleep") is not None:
                        delay = kwargs["sleep"]
                    sleep_(delay)

                if logger.isEnabledFor(level):
                    self._log_action(level, func.__name__, args, kwargs, result, time.perf_counter() - start)

                log_screenshot(
                    self.parameters.screenshot,
                    func.__name__,
                    args,
                    kwargs,
                    kwargs.get("on") or kwargs.get("element"),
                    lambda: self._log_capture(func.__name__, result),
                    self.mouse_position,
                    result,
                )

                return result

        return wrapper

    return decorator


@dataclass
class ElementResult:
    success: bool
    time: float | None = None
    match: Match | None = None


@dataclass
class WaitResult:
    results: dict[str, ElementResult]

    def get(self, key: str) -> ElementResult | None:
        return self.results.get(key)

    def __bool__(self):
        return all(res.success for res in self.results.values())


@dataclass(frozen=True)
class Detection:
    """How an element was found, for the logs."""

    method: str | None
    variant: str | None = None
    screen: int | None = None
    confidence: float | None = None

    @classmethod
    def of(cls, report: LocateReport, index: int) -> "Detection":
        """Tells how a match of a report was found.

        :param report: Report of the search.
        :param index: Index of the match in the report.
        :return: The method, variant, screen and confidence of the match.
        """
        if report.fixed_position:
            return cls("fixed position")
        match = report.matches[index]
        variant = report.variants[report.match_variants[index]]
        return cls(variant.method, variant.variant.name, report.match_screens[index], round(match.confidence, 3))

    def __str__(self) -> str:
        parts = [self.method or "unknown method"]
        if self.variant:
            parts.append(f"variant {self.variant}")
        if self.screen is not None:
            parts.append(f"screen {self.screen}")
        if self.confidence is not None:
            parts.append(f"confidence {self.confidence:.2f}")
        return ", ".join(parts)


def _shorten(text: str, length: int = 80) -> str:
    """Cuts a long text to log it on one line."""
    text = " ".join(text.split())
    return text if len(text) <= length else f"{text[: length - 3]}..."


EDITOR_MESSAGES = {
    "ELEMENT NOT DEFINED": "Element not defined yet",
    "INVALID ELEMENT": "Element not valid",
    "ELEMENT NOT FOUND ON SCREEN": "Element not found on screen",
}
"""Why the editor opens, as the new editor shows it."""


class Controller:
    def __init__(self, parameters: ParametersType = None):
        match parameters:
            case None:
                self.parameters = Parameters()
            case dict():
                self.parameters = Parameters.from_dict(parameters)
            case Path() | str():
                self.parameters = Parameters.from_file(parameters)
            case Parameters():
                self.parameters = parameters
            case _:
                raise TypeError(f"Unsupported parameters type: {type(parameters)}")

        if errors := self.parameters.resolve():
            raise ModelError("Parameters", errors)

        params: dict[str, Any] = {}
        if self.parameters.execution_mode == "vnc":
            assert self.parameters.vnc is not None
            params = self.parameters.vnc.to_dict()

        self._pause_manager = PauseManager(self.parameters.pause_shortcut)
        self._driver = PausableDriver(DRIVERS[self.parameters.execution_mode](**params), self._pause_manager)
        self._root_action: str | None = None
        self._detections: dict[str, Detection] = {}
        self._workspace = DataWorkspace()
        self._ignored_screens: set[int] = set()
        self._unfit_screens: set[tuple[str, str, int]] = set()

        # In VNC mode, the remote screen is only available after connect()
        self._run_checks(datasets=True, screen=self.parameters.execution_mode == "local")

        logger.info(
            "Controller ready: %s mode",
            self.parameters.execution_mode,
            extra=fields(action="init", mode=self.parameters.execution_mode),
        )
        if logger.isEnabledFor(logging.DEBUG):
            settings = self.parameters.to_dict(json_mode=True)
            if settings.get("vnc", {}).get("password") is not None:
                settings["vnc"]["password"] = "***"
            logger.debug("Parameters: %s", settings)

    def connect(self) -> None:
        """For remote modes that require starting a session."""
        self._driver.connect()

        if self.parameters.execution_mode == "vnc":
            self._run_checks(datasets=False, screen=True)

    def close(self) -> None:
        """For remote modes that require closing a session."""
        self._driver.close()

    def replay(self, replay: Replay) -> None:
        if not replay.resolved:
            if errs := replay.resolve():
                raise ModelError("Replay", errs)

        events = replay.load().events
        start = time.perf_counter()
        Player(self._driver).start(events)
        duration = time.perf_counter() - start
        logger.log(
            self._level(),
            "replay %s: %d events in %.2f s",
            replay.name,
            len(events),
            duration,
            extra=fields(action="replay", replay=replay.name, events=len(events), duration=round(duration, 3)),
        )

    @property
    def mouse_position(self) -> Point:
        return Point(*self._driver.mouse_position())

    def screen_size(self, *, screen: int | None = None) -> tuple[int, int]:
        """Gives the size of a screen.

        :param screen: Screen number; None means the default screen, the first one if it is a list.
        :return: The (width, height) of the screen.
        :raises ValueError: If the screen does not exist.
        """
        number = self._screen(screen)
        if screens := self._driver.screens():
            if not 0 <= number < len(screens):
                raise ValueError(f"Screen {number} does not exist: {len(screens) - 1} screens available")
            return screens[number].width, screens[number].height
        img = self._driver.capture(number)
        return img.shape[:2][::-1]

    def screenshot(
        self,
        *,
        screen: int | None = None,
        screen_area: Area | ScreenArea | None = None,
        path: Path | str | None = None,
    ) -> np.ndarray:
        """Captures a screen, or an area of it.

        :param screen: Screen number; None means the default screen, the first one if it is a list.
        :param screen_area: Area to keep, relative to the screen.
        :param path: File to save the image to.
        :return: The captured image (RGB).
        """
        number = self._screen(screen)
        image = self._driver.capture(number)

        if area := to_area(screen_area, image):
            x, y, w, h = area.as_xywh()
            image = image[y : y + h, x : x + w]

        if path:
            cv.imwrite(str(path), cv.cvtColor(image, cv.COLOR_RGB2BGR))

        h, w = image.shape[:2]
        logger.log(
            self._level(),
            "screenshot of screen %s (%dx%d)%s",
            number,
            w,
            h,
            f" saved to {path}" if path else "",
            extra=fields(action="screenshot", screen=number, size=[w, h], path=str(path) if path else None),
        )
        return image

    def pixel_color(self, x, y):
        raise NotImplementedError

    @handle_action(sleep_after=False, use_wait=False)
    def locate(self, element: Element | None = None) -> list[Match]:
        return self._locate_element(element=element)

    @handle_action(sleep_after=False, use_wait=False)
    def wait(self, *, on: Elements = None, off: Elements = None) -> WaitResult:
        return self._wait(on=on, off=off)

    def read_text(
        self,
        *,
        screen: int | None = None,
        screen_area: Area | ScreenArea | None = None,
        fidelity: OcrFidelity = OcrFidelity.ACCURATE,
    ) -> str:
        """Reads the text of a screen, or of an area of it.

        :param screen: Screen number; None means the default screen, the first one if it is a list.
        :param screen_area: Area to read, relative to the screen.
        :param fidelity: OCR fidelity.
        :return: The text read.
        """
        with self._acting("read_text") as level:
            start = time.perf_counter()
            text = Ocr().read_text_on_image(self.screenshot(screen=screen, screen_area=screen_area), fidelity)
            duration = time.perf_counter() - start
            logger.log(
                level,
                "read_text on screen %s: %r in %.2f s",
                self._screen(screen),
                _shorten(text),
                duration,
                extra=fields(
                    action="read_text", screen=self._screen(screen), chars=len(text), duration=round(duration, 3)
                ),
            )
            return text

    def locate_text(
        self,
        text: str,
        *,
        screen: int | list[int] | None = None,
        screen_area: Area | ScreenArea | None = None,
        fidelity: OcrFidelity = OcrFidelity.FAST,
        confidence_threshold: float = 0.8,
    ) -> list[Match]:
        """Locates a text on one or several screens.

        :param text: Text to find.
        :param screen: Screen number or list of screen numbers; None means the default screens.
        :param screen_area: Area to search, applied to each screen.
        :param fidelity: OCR fidelity.
        :param confidence_threshold: Minimum OCR confidence.
        :return: Every occurrence, in desktop coordinates.
        """
        screen = self.parameters.default.screen if screen is None else screen
        self._report_ignored_screens(screen)
        with self._acting("locate_text") as level:
            start = time.perf_counter()
            matches = locate_text_on_screens(
                text, self._driver.capture, self._driver.screens(), screen, screen_area, fidelity, confidence_threshold
            )
            duration = time.perf_counter() - start
            first = matches[0].target if matches else None
            logger.log(
                level,
                "locate_text %r: %s in %.2f s",
                text,
                f"{len(matches)} match(es), first at {tuple(first)}" if first else "not found",
                duration,
                extra=fields(
                    action="locate_text",
                    text=text,
                    success=bool(matches),
                    matches=len(matches),
                    target=list(first) if first else None,
                    duration=round(duration, 3),
                ),
            )
            return matches

    @handle_action()
    def move(self, *, on: Element | None = None, sleep: SleepType = None) -> None:
        self._move(on)

    @handle_action()
    def click(
        self, *, on: Element | None = None, button: Button = Button.LEFT, count: int = 1, sleep: SleepType = None
    ) -> None:
        self._click(on, button, count)

    @handle_action()
    def double_click(self, *, on: Element | None = None, button: Button = Button.LEFT, sleep: SleepType = None) -> None:
        self._click(on, button, 2)

    @handle_action()
    def triple_click(self, *, on: Element | None = None, button: Button = Button.LEFT, sleep: SleepType = None) -> None:
        self._click(on, button, 3)

    @handle_action()
    def right_click(self, *, on: Element | None = None, sleep: SleepType = None) -> None:
        self._click(on, Button.RIGHT, 1)

    @handle_action()
    def scroll(self, *, v: int = 0, h: int = 0, on: Element | None = None, sleep: SleepType = None) -> None:
        self._move_and_pause(on)
        self._driver.mouse_scroll(v, h)

    @handle_action()
    def drag(self, *, on: Element | None = None, button: Button = Button.LEFT, sleep: SleepType = None) -> None:
        self._down(button)
        self._move_and_pause(on)
        self._up(button)

    @handle_action(update_element=False, use_wait=False)
    def type(self, text: str, interval: float = 0, sleep: SleepType = None) -> None:
        if interval == 0:
            self._driver.paste(text)
            return

        self._driver.type_one_by_one(text, lambda: sleep_(interval))

    @handle_action(update_element=False, use_wait=False)
    def press(self, *keys: Key, interval: float = 0, sleep: SleepType = None) -> None:
        for key in keys:
            self._driver.key_down(key)
            sleep_(interval)
        for key in reversed(keys):
            self._driver.key_up(key)

    @handle_action(sleep_after=False, update_element=False, use_wait=False)
    def down(self, *args: Key | Button) -> None:
        self._down(*args)

    @handle_action(sleep_after=False, update_element=False, use_wait=False)
    def up(self, *args: Key | Button) -> None:
        self._up(*args)

    @contextmanager
    def hold(self, *args: Key | Button):
        self._down(*args)
        try:
            yield
        finally:
            self._up(*args)

    @handle_action(update_element=False, use_wait=False)
    def scroll_until(
        self, v: int = 0, h: int = 0, element: Element | None = None, timeout: float = 60, sleep: SleepType = None
    ) -> Match | None:
        start = time.perf_counter()
        suspended_at_start = self._driver.suspended_time
        before, after = np.array([0]), np.array([1])
        while similarity_index(before, after) < 1:
            if element and (match := self.locate(element=element)):
                return match[0]

            if time.perf_counter() - start - (self._driver.suspended_time - suspended_at_start) >= timeout:
                return None

            # What scrolls is the window under the mouse: compare the screen showing the mouse.
            screen = screen_at(self.mouse_position, self._driver.screens())
            before = self.screenshot(screen=screen)
            self.scroll(v=v, h=h)
            after = self.screenshot(screen=screen)

        return None

    @handle_action(update_element=False, use_wait=False)
    def browse_menu(self, *elements: Element, menu: Menu = Menu.HORIZONTAL, sleep: SleepType = None) -> None:
        if not elements:
            return

        directions = [MouseDirection.XY_X, MouseDirection.XY_Y]
        # The menu opens on the screen of its first element; the next ones are searched on that screen.
        screens = self._driver.screens()
        wanted = elements[0].screen if elements[0].screen is not None else self.parameters.default.screen
        among = isinstance(wanted, list) and bool(screens)
        # Among several screens, the menu screen is only known once clicked: capture all screens before.
        screen = 0 if among else self._screen(wanted)
        before = self.screenshot(screen=screen)
        self.click(on=elements[0])

        if len(elements) == 1:
            return

        if among:
            screen = screen_at(self.mouse_position, screens) or self._screen(wanted)
            before = crop_screen(before, screens, screen)

        search_area = None
        for idx, element in enumerate(elements[1:], start=menu.value):
            after = self.screenshot(screen=screen)
            changed = diff_area(before, after)
            if changed:
                x, y, w, h = changed
                search_area = Area(left=x, top=y, right=x + w, bottom=y + h)

            is_last = idx == menu.value + len(elements) - 2
            overrides: dict[str, MouseDirection | Area | int] = {
                "mouse_direction": directions[menu.value if is_last else (idx + 1) % 2],
                "screen": screen,
            }
            if search_area is not None:
                overrides["search_area"] = search_area

            before = after
            if is_last:
                self.click(on=element(**overrides))
            else:
                self.move(on=element(**overrides))

    @contextmanager
    def _acting(self, action: str):
        """Marks the action in progress, the first one being the action the user called.

        :param action: Name of the action starting.
        :return: The level to log the action at: INFO for the action the user called, DEBUG for the ones it calls.
        """
        is_initiator = self._root_action is None
        if is_initiator:
            self._root_action = action
            self._detections = {}
        try:
            yield logging.INFO if is_initiator else logging.DEBUG
        finally:
            if is_initiator:
                self._root_action = None

    def _level(self) -> int:
        """Level to log a method that is not an action: INFO when the user calls it, DEBUG when an action does."""
        return logging.INFO if self._root_action is None else logging.DEBUG

    def _log_action(self, level: int, action: str, args: tuple, kwargs: dict, result: Any, duration: float) -> None:
        """Logs an action once done, with what it acted on and how its element was found.

        :param level: Level of the log.
        :param action: Name of the action.
        :param args: Positional arguments of the action.
        :param kwargs: Keyword arguments of the action, elements prepared.
        :param result: Result of the action.
        :param duration: Seconds the action took, wait for the elements included.
        """
        values: dict[str, Any] = {"action": action, "duration": round(duration, 3), "success": True}
        detail = ""

        if action == "wait":
            detail, values["success"] = self._describe_wait(kwargs, result), bool(result)
        elif action in ("locate", "scroll_until"):
            element = kwargs.get("element")
            if element is None and args:
                element = args[2] if action == "scroll_until" and len(args) > 2 else args[0]
            match = (result[0] if result else None) if action == "locate" else result
            values["success"] = match is not None
            if element is not None:
                values["element"] = element.name
                detail = f" {element.name}"
            if match is None:
                detail += ": not found"
            else:
                values["target"] = list(match.target)
                detail += f": found at {tuple(match.target)}"
                if action == "locate":
                    values["matches"] = len(result)
                    detail += f" ({len(result)} match(es))"
                detail += self._describe_detection(element, values)
        elif action == "type":
            values["text"] = mask(args[0]) if args else ""
            detail = f" {values['text']!r}"
        elif action in ("press", "down", "up"):
            values["keys"] = [arg.name for arg in args]
            detail = " " + "+".join(values["keys"])
        elif action == "browse_menu":
            values["elements"] = [element.name for element in args]
            detail = " " + " > ".join(values["elements"])
        else:  # mouse actions: move, click, double_click, triple_click, right_click, scroll, drag
            if action == "click" and kwargs.get("button", Button.LEFT) != Button.LEFT:
                detail += f" {kwargs['button'].name.lower()}"
            if kwargs.get("count", 1) != 1:
                detail += f" x{kwargs['count']}"
            if action == "scroll":
                detail += f" v={kwargs.get('v', 0)} h={kwargs.get('h', 0)}"
            element = kwargs.get("on")
            if element is not None:
                values["element"] = element.name
                detail += f" on {element.name}"
            position = self.mouse_position
            values["target"] = list(position)
            detail += f" at {tuple(position)}"
            detail += self._describe_detection(element, values)

        logger.log(level, "%s%s in %.2f s", action, detail, duration, extra=fields(**values))

    def _describe_detection(self, element: Element | None, values: dict[str, Any]) -> str:
        """Describes how an element was found during the action, and adds it to the fields of the log.

        :param element: Element acted on.
        :param values: Fields of the log, completed with the method, variant, screen and confidence.
        :return: The description, e.g. `` [template, variant DEFAULT, screen 1]``; empty if it was not searched.
        """
        if element is None or (detection := self._detections.get(element.name)) is None:
            return ""
        values.update(
            method=detection.method,
            variant=detection.variant,
            screen=detection.screen,
            confidence=detection.confidence,
        )
        return f" [{detection}]"

    def _describe_wait(self, kwargs: dict, result: WaitResult) -> str:
        """Describes the outcome of a wait, element by element.

        :param kwargs: Keyword arguments of the wait.
        :param result: Result of the wait.
        :return: The description, e.g. `` on LOGIN (found in 0.30 s [template, ...]), off SPINNER (gone in 1.20 s)``.
        """
        parts = []
        for param, word in (("on", "found"), ("off", "gone")):
            elements = kwargs.get(param)
            if elements is None:
                continue
            outcomes = []
            for element in elements if isinstance(elements, (list, tuple)) else [elements]:
                outcome = result.get(element.name)
                if outcome is None or not outcome.success:
                    outcomes.append(f"{element.name} (timeout)")
                    continue
                detection = self._detections.get(element.name) if param == "on" else None
                found = f" [{detection}]" if detection else ""
                outcomes.append(f"{element.name} ({word} in {outcome.time or 0:.2f} s{found})")
            parts.append(f"{param} {', '.join(outcomes)}")
        return " " + ", ".join(parts) + (": success" if result else ": failed")

    def _prepare_element(self, raw: Element, update: bool, wait: bool) -> Element | None:
        while True:
            element, problem = self._diagnose(raw, update, wait)
            if problem is None:
                return element

            message, error = problem
            if not self.parameters.debug_elements or not raw.alias:
                raise error

            logger.info(
                "%s: %s, opening the editor",
                raw.name,
                EDITOR_MESSAGES.get(message, message).lower(),
                extra=fields(action=self._root_action, element=raw.name, reason=message),
            )
            if not (edited := self._trigger_editor(raw, message)):
                return None

            raw = edited

    def _diagnose(self, raw: Element, update: bool, wait: bool) -> tuple[Element | None, tuple[str, Exception] | None]:
        if raw.is_new:
            return None, ("ELEMENT NOT DEFINED", Exception(f"Element {raw.name} is not defined"))

        if errors := raw.resolve():
            return None, ("INVALID ELEMENT", ModelError(f"Element {raw.name}", errors))

        element = self._update(raw) if update else raw
        if not wait:
            return element, None

        if not (wait_result := self._wait(on=element)):
            return None, ("ELEMENT NOT FOUND ON SCREEN", Exception(f"Element {raw.name} not found on screen"))

        match = wait_result.results[element.name].match
        assert match is not None  # a successful wait on an element always carries its match
        # The match is in desktop coordinates, which screen 0 uses for a fixed position: the match may be on any
        # screen of a list, left of or above its first one. A driver unable to list screens has only one.
        screen = 0 if self._driver.screens() else element.screen
        return element(x=match.target.x, y=match.target.y, rel_x=None, rel_y=None, screen=screen), None

    def _update(self, element: Element):
        element = element.update(self.parameters.default, overwrite=False)
        element.variants = [
            variant.update(element, exclude={"name"}, overwrite=False) for variant in element.variants or []
        ]
        return element

    def _trigger_editor(self, element: Element, message: str) -> Element | None:
        overrides = {name: getattr(element, name) for name in element.overridden_fields}

        with self._driver.suspended():
            if legacy_editor_enabled():
                result = EditorResult(self._open_legacy_editor(element, message))
            else:
                result = self._open_new_editor(element, message, overrides)
            if result.element is not None:
                self._persist_element(result.element)  # saved before waiting, in case the run is stopped meanwhile
            logger.info(
                "%s: editor closed, %s",
                element.name,
                "element saved" if result.element is not None else "nothing saved",
                extra=fields(element=element.name, saved=result.element is not None, resume=result.resume.value),
            )
            self._wait_to_resume(result.resume)

        edited = result.element
        if edited is None:
            return None
        return edited(**overrides) if overrides else edited

    def _open_legacy_editor(self, element: Element, message: str) -> Element | None:
        """Opens the old editor, kept as a fallback with GUIMAUVE_EDITOR=legacy."""
        from guimauve.gui.element_editor_legacy import Context, start_element_editor

        edited, to_save = start_element_editor(
            Context(
                element=element.without_overrides(),
                default=self.parameters.default,
                capture_provider=lambda: self._driver.capture(1),
                message=message,
                action=self._root_action or "manual_call",
            )
        )
        return edited if to_save else None

    def _open_new_editor(self, element: Element, message: str, overrides: dict[str, Any]) -> EditorResult:
        """Opens the element editor, the default one."""
        from guimauve.gui.element_editor import Context, start_element_editor

        return start_element_editor(
            Context(
                element=element.without_overrides(),
                default=self.parameters.default,
                capture_provider=self._driver.capture,
                message=EDITOR_MESSAGES.get(message, message),
                action=self._root_action or "manual_call",
                code_overrides=overrides,
                screens=self._driver.screens(),
                from_run=True,
                mouse_position=self.mouse_position,
            )
        )

    def _wait_to_resume(self, mode: ResumeMode) -> None:
        """Waits as chosen in the editor before the run resumes, while the driver is still suspended.

        The wait is not counted in the timeout of the element, and the mouse goes back where the run left it only
        once it is over. Paused, the run resumes with the pause shortcut, as any pause.
        """
        if mode.delay is None:
            shortcut = "+".join(key.name.title() for key in self.parameters.pause_shortcut)
            logger.info("Run paused: press %s to resume", shortcut)
            self._pause_manager.pause()
            self._pause_manager.wait_while_paused()
        elif mode.delay:
            logger.info("Run resuming in %g s", mode.delay)
            sleep_(mode.delay)

    def _persist_element(self, element: Element) -> None:
        assert element.alias is not None
        element._is_new = False
        save_element(self._workspace, element.alias, element)
        sync_dataset(self._workspace, element.alias)

        module = importlib.import_module(f"guimauve.data.{element.alias}")
        setattr(module.Elements, element.name, element)

    def _locate_element(self, element: Element | None = None) -> list[Match]:
        if element is None:
            return []

        self._report_ignored_screens(element.screen)
        report = locate_element(element, self._driver.capture, self._driver.screens(), self.mouse_position)
        self._report_unfit_screens(element, report)
        if report.fixed_position and element.name not in self._detections:
            target = report.matches[0].target
            # Logged with the detection; once found, an element is located again at its position to move to it
            detection_logger.debug(
                "%s: fixed position %s",
                element.name,
                tuple(target),
                extra=fields(element=element.name, target=list(target)),
            )
        if report.matches:
            index = element.match_index if element.match_index is not None else 0
            # Kept for the log of the action: the first search tells how the element was found, the next ones only
            # move to the position it was found at
            self._detections.setdefault(element.name, Detection.of(report, min(index, len(report.matches) - 1)))
        return report.matches

    def _screen(self, screen: int | list[int] | None = None) -> int:
        """Picks the screen to capture for a single image.

        A driver that cannot list screens (VNC) captures its only screen whatever the number: a number other than 1
        is reported once.

        :param screen: Screen number or list of screen numbers; None means the default screen.
        :return: The given screen, else the default one; the first screen of a list.
        """
        screen = self.parameters.default.screen if screen is None else screen
        screen = screen[0] if isinstance(screen, list) else screen
        if screen is None:
            return 1
        self._report_ignored_screens(screen)
        return screen

    def _report_ignored_screens(self, screen: int | list[int] | None) -> None:
        """Warns once per screen number that a driver unable to list screens (VNC) ignores.

        :param screen: Screen number or list of screen numbers requested.
        """
        if self._driver.screens():
            return
        numbers = screen if isinstance(screen, list) else ([] if screen is None else [screen])
        for number in numbers:
            if number != 1 and number not in self._ignored_screens:
                self._ignored_screens.add(number)
                logger.warning(
                    "The driver exposes a single screen: screen %s is ignored, the whole screen is used", number
                )

    def _report_unfit_screens(self, element: Element, report: LocateReport) -> None:
        """Warns once per variant and screen skipped because the image is larger than the search area.

        :param element: Element that was located.
        :param report: Outcome of the location.
        """
        for variant_report in report.variants:
            for screen in variant_report.unfit_screens:
                key = (element.name, variant_report.variant.name, screen)
                if key not in self._unfit_screens:
                    self._unfit_screens.add(key)
                    logger.warning(
                        "Variant %s of %s is larger than the search area of screen %s: this screen is skipped",
                        key[1],
                        key[0],
                        screen,
                    )

    def _log_capture(self, action: str, result) -> tuple[np.ndarray, tuple[int, int]]:
        """Captures the screen to log: the one of the first match for ``locate``, else the one under the mouse.

        :param action: Name of the action logged.
        :param result: Result of the action.
        :return: The image of that screen and the desktop position of its top-left corner.
        """
        screens = self._driver.screens()
        if not screens:
            return self.screenshot(), (0, 0)
        matches = result if action == "locate" and isinstance(result, list) else []
        point = matches[0].target if matches else self.mouse_position
        screen = screen_at(point, screens) or self._screen()
        return self.screenshot(screen=screen), screen_origin(screen, screens)

    def _wait(self, *, on: Elements = None, off: Elements = None) -> WaitResult:
        if isinstance(on, Element):
            on = [on]
        if isinstance(off, Element):
            off = [off]

        names = [element.name for element in [*(on or []), *(off or [])]]
        if duplicates := sorted({name for name in names if names.count(name) > 1}):
            raise ValueError(f"Cannot wait on several elements with the same name: {', '.join(duplicates)}.")

        results = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                **{executor.submit(self._check_element, element, True): element for element in on or []},
                **{executor.submit(self._check_element, element, False): element for element in off or []},
            }
            for future, element in futures.items():
                results[element.name] = ElementResult(*future.result())

        return WaitResult(results)

    def _check_element(self, element: Element, on_screen: bool) -> tuple[bool, float | None, Match | None]:
        start = time.perf_counter()
        suspended_at_start = self._driver.suspended_time
        assert element.timeout is not None
        assert element.match_index is not None
        searches = 0
        while (
            current := time.perf_counter() - start - (self._driver.suspended_time - suspended_at_start)
        ) < element.timeout:
            matches = self._locate_element(element=element)
            searches += 1
            if on_screen and matches:
                try:
                    match = matches[element.match_index]
                except IndexError:
                    length = len(matches)
                    raise Exception(
                        f"Cannot reach match index [{element.match_index}] for Element {element.name}. "
                        f"Valid range is [0-{length - 1}] ({length} matches found)."
                    )
                logger.debug(
                    "%s found after %d search(es) in %.2f s",
                    element.name,
                    searches,
                    current,
                    extra=fields(element=element.name, searches=searches, duration=round(current, 3)),
                )
                return True, current, match
            if not on_screen and not matches:
                logger.debug(
                    "%s gone after %d search(es) in %.2f s",
                    element.name,
                    searches,
                    current,
                    extra=fields(element=element.name, searches=searches, duration=round(current, 3)),
                )
                return True, current, None
            sleep_(min(POLL_INTERVAL, element.timeout - current))
        logger.debug(
            "%s still %s after %d search(es): timeout of %g s",
            element.name,
            "missing" if on_screen else "on screen",
            searches,
            element.timeout,
            extra=fields(element=element.name, searches=searches, timeout=element.timeout),
        )
        return False, None, None

    def _move(self, on: Element | None) -> None:
        if on is None:
            return

        end = self._locate_element(element=on)[0].target

        if not on.mouse_speed:
            self._driver.mouse_move(*end)
            return

        if on.mouse_direction is None:
            return

        start = self.mouse_position
        positions = {
            MouseDirection.STRAIGHT: [[start, end]],
            MouseDirection.XY_X: [[start, Point(end.x, start.y)], [Point(end.x, start.y), end]],
            MouseDirection.XY_Y: [[start, Point(start.x, end.y)], [Point(start.x, end.y), end]],
        }

        for start, end in positions.get(on.mouse_direction, []):
            self._move_smooth(start, end, on.mouse_speed)

    def _move_and_pause(self, on: Element | None) -> None:
        """Moves to the element, then pauses so the target can react to the hover."""
        if on:
            self._move(on)
            sleep_(self.parameters.sleep)

    def _move_smooth(self, start: tuple[int, int], end: tuple[int, int], speed: float | int):
        start_x, start_y = start
        end_x, end_y = end

        distance = math.hypot(end_x - start_x, end_y - start_y)
        if distance == 0:
            return

        duration = distance / speed
        steps = min(max(int(distance), 1), 100)
        interval = duration / steps

        for step in range(steps + 1):
            t = step / steps
            new_x = int(start_x + (end_x - start_x) * t)
            new_y = int(start_y + (end_y - start_y) * t)
            self._driver.mouse_move(new_x, new_y)
            sleep_(interval)

    def _click(self, on: Element | None, button: Button, count: int) -> None:
        self._move_and_pause(on)
        for _ in range(count):
            self._driver.mouse_down(button)
            self._driver.mouse_up(button)

    def _down(self, *args: Key | Button) -> None:
        for arg in args:
            if isinstance(arg, Key):
                self._driver.key_down(arg)
            elif isinstance(arg, Button):
                self._driver.mouse_down(arg)
            else:
                raise ValueError(f"Unsupported argument {type(arg)}, must be Key or Button")

    def _up(self, *args: Key | Button) -> None:
        for arg in args:
            if isinstance(arg, Key):
                self._driver.key_up(arg)
            elif isinstance(arg, Button):
                self._driver.mouse_up(arg)
            else:
                raise ValueError(f"Unsupported argument {type(arg)}, must be Key or Button")

    def _run_checks(self, *, datasets: bool, screen: bool) -> None:
        """Runs every enabled check, then raises a single error listing all failures."""
        checks = self.parameters.checks
        results: list[str | None] = []

        if datasets:
            for alias in selected_datasets(self._workspace, checks.datasets):
                results.append(check_dataset(self._workspace, alias))
        if screen:
            for screen_check in checks.screen or []:
                results += self._check_screen(screen_check)

        if failures := [result for result in results if result is not None]:
            raise EnvironmentCheckError(failures)
        if results:
            logger.debug("Environment checks passed (%d)", len(results), extra=fields(checks=len(results)))

    def _check_screen(self, screen_check: ScreenCheck) -> list[str | None]:
        """Checks the size and scaling of one screen."""
        number = screen_check.number
        if screens := self._driver.screens():
            if failure := check_screen_exists(number, screens):
                return [failure]
        elif number != 1:
            logger.warning("Screen check skipped for screen %s: the driver exposes a single screen", number)
            return []

        results: list[str | None] = []
        if screen_check.size is not None:
            results.append(check_screen_size(number, screen_check.size, self.screen_size(screen=number)))
        if screen_check.scaling is not None:
            results.append(check_scaling(number, screen_check.scaling, self.parameters.execution_mode))
        return results
