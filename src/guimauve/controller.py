import importlib
import logging
import math
import time
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, TypeAlias

import cv2 as cv
import numpy as np

from guimauve.detection.detector import Match, Point
from guimauve.detection.feature_matching import FeatureMatching
from guimauve.detection.ocr import Ocr
from guimauve.detection.template_matching import TemplateMatching
from guimauve.drivers.local.driver import LocalDriver
from guimauve.drivers.pausable_driver import PausableDriver
from guimauve.drivers.vnc.driver import VNCDriver
from guimauve.enums import Button, Key, MatchSort, Menu, MouseDirection, OcrFidelity, ScreenArea
from guimauve.log_screenshot import log_screenshot
from guimauve.models.area import Area
from guimauve.models.data import Data
from guimauve.models.element import Element
from guimauve.models.model import ModelError
from guimauve.models.parameters import Parameters
from guimauve.models.replay import Replay
from guimauve.models.variant import ImageVariant, Target, TextVariant
from guimauve.pause_manager import PauseManager
from guimauve.recorder.player import Player
from guimauve.storage.save import save_element
from guimauve.storage.sync import sync_dataset
from guimauve.storage.workspace import DataWorkspace
from guimauve.utils.image import diff_area, similarity_index
from guimauve.utils.time import sleep as sleep_

logger = logging.getLogger(__name__)

DataType: TypeAlias = Data | Path | dict | str | None
ParametersType: TypeAlias = Parameters | Path | dict | str | None
SleepType: TypeAlias = int | float | None
Elements: TypeAlias = Element | Iterable[Element] | None

POLL_INTERVAL = 0.05

DETECTORS = {"template": TemplateMatching, "feature": FeatureMatching, "ocr": Ocr}
DRIVERS = {"local": LocalDriver, "vnc": VNCDriver}


def get_elements_kwargs(kwargs: dict) -> dict[str, Sequence[Element]]:
    elements: dict[str, Sequence[Element]] = {}
    for param in ("element", "on", "off"):
        if param in kwargs:
            elements_value = kwargs[param]
            elements[param] = elements_value if isinstance(elements_value, (tuple, list)) else [elements_value]

    return elements


def to_area(screen_area: Area | ScreenArea | None, screen: np.ndarray) -> Area | None:
    """Converts a screen area to an absolute Area, sized from the given screen for a ScreenArea."""
    if isinstance(screen_area, ScreenArea):
        h, w, _ = screen.shape
        return screen_area.get_area((w, h))
    return screen_area


def handle_action(update_element: bool = True, use_wait: bool = True, sleep_after: bool = True):
    """Performs actions before and after the decorated method execution.

    :param update_element: If True, updates the element with default element parameters before executing action.
    :param use_wait: If True, use the wait method to ensure the element is present before executing action.
    :param sleep_after: If True, sleeps for a defined duration after executing action.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            is_initiator = False
            if self._root_action is None:
                self._root_action = func.__name__
                is_initiator = True

            try:
                elements_params = get_elements_kwargs(kwargs)

                for param_name, element_list in elements_params.items():
                    updated_list = []
                    for element in element_list:
                        if not (element := self._prepare_element(element, update=update_element, wait=use_wait)):
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

                log_screenshot(
                    self.parameters.screenshot,
                    func.__name__,
                    args,
                    kwargs,
                    kwargs.get("on") or kwargs.get("element"),
                    self.screenshot,
                    self.mouse_position,
                    result,
                )

                return result
            finally:
                if is_initiator:
                    self._root_action = None

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
        self._root_action = None
        self._workspace = DataWorkspace()

    def connect(self) -> None:
        """For remote modes that require starting a session."""
        self._driver.connect()

    def close(self) -> None:
        """For remote modes that require closing a session."""
        self._driver.close()

    def replay(self, replay: Replay) -> None:
        if not replay.resolved:
            if errs := replay.resolve():
                raise ModelError("Replay", errs)

        Player(self._driver).start(replay.load().events)

    @property
    def mouse_position(self) -> Point:
        return Point(*self._driver.mouse_position())

    @property
    def screen_size(self) -> tuple[int, int]:
        img = self._driver.capture()
        return img.shape[:2][::-1]

    def screenshot(self, screen_area: Area | ScreenArea | None = None, path: Path | str | None = None) -> np.ndarray:
        screen = self._driver.capture()

        if area := to_area(screen_area, screen):
            x, y, w, h = area.as_xywh()
            screen = screen[y : y + h, x : x + w]

        if path:
            cv.imwrite(str(path), cv.cvtColor(screen, cv.COLOR_RGB2BGR))

        return screen

    def pixel_color(self, x, y):
        raise NotImplementedError

    @handle_action(sleep_after=False, use_wait=False)
    def locate(self, element: Element | None = None) -> list[Match]:
        return self._locate_element(element=element)

    @handle_action(sleep_after=False, use_wait=False)
    def wait(self, *, on: Elements = None, off: Elements = None) -> WaitResult:
        return self._wait(on=on, off=off)

    def read_text(
        self, screen_area: Area | ScreenArea | None = None, fidelity: OcrFidelity = OcrFidelity.ACCURATE
    ) -> str:
        return Ocr().read_text_on_image(self.screenshot(screen_area=screen_area), fidelity)

    def locate_text(
        self,
        text: str,
        screen_area: Area | ScreenArea | None = None,
        fidelity: OcrFidelity = OcrFidelity.FAST,
        confidence_threshold: float = 0.8,
    ) -> list[Match]:
        screen = self._driver.capture()
        area = to_area(screen_area, screen)
        return Ocr().locate_text_on_image(
            screen,
            text,
            fidelity,
            confidence_threshold,
            area=area.as_xywh() if area else None,
        )

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

        for char in text:
            self._driver.type(char)
            sleep_(interval)

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

    @handle_action(sleep_after=False, update_element=False, use_wait=False)
    @contextmanager
    def hold(self, *args: Key | Button, sleep: SleepType = None):
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

            before = self.screenshot()
            self.scroll(v=v, h=h)
            after = self.screenshot()

        return None

    @handle_action(update_element=False, use_wait=False)
    def browse_menu(self, *elements: Element, menu: Menu = Menu.HORIZONTAL, sleep: SleepType = None) -> None:
        if not elements:
            return

        directions = [MouseDirection.XY_X, MouseDirection.XY_Y]
        before = self.screenshot()
        self.click(on=elements[0])

        if len(elements) == 1:
            return

        search_area = None
        for idx, element in enumerate(elements[1:], start=menu.value):
            after = self.screenshot()
            changed = diff_area(before, after)
            if changed:
                x, y, w, h = changed
                search_area = Area(left=x, top=y, right=x + w, bottom=y + h)

            is_last = idx == menu.value + len(elements) - 2
            overrides: dict[str, MouseDirection | Area] = {
                "mouse_direction": directions[menu.value if is_last else (idx + 1) % 2]
            }
            if search_area is not None:
                overrides["search_area"] = search_area

            before = after
            if is_last:
                self.click(on=element(**overrides))
            else:
                self.move(on=element(**overrides))

    def _prepare_element(self, raw: Element, update: bool, wait: bool) -> Element | None:
        while True:
            element, problem = self._diagnose(raw, update, wait)
            if problem is None:
                return element

            message, error = problem
            if not self.parameters.debug_elements or not raw.alias:
                raise error

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
        x, y = match.target
        return element(x=x, y=y, rel_x=None, rel_y=None), None

    def _update(self, element: Element):
        element = element.update(self.parameters.default, overwrite=False)
        element.variants = [
            variant.update(element, exclude={"name"}, overwrite=False) for variant in element.variants or []
        ]
        return element

    def _trigger_editor(self, element: Element, message: str) -> Element | None:
        from guimauve.gui.element_editor import Context, start_element_editor

        overrides = {name: getattr(element, name) for name in element.overridden_fields}

        with self._driver.suspended():
            edited, to_save = start_element_editor(
                Context(
                    element=element.without_overrides(),
                    default=self.parameters.default,
                    capture_provider=self._driver.capture,
                    message=message,
                    action=self._root_action or "manual_call",
                )
            )
        if not to_save:
            return None

        self._persist_element(edited)
        return edited(**overrides) if overrides else edited

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

        if element.has_coordinates():
            x, y = element.resolve_coordinates(*self.mouse_position)
            return [Match(box=None, target=Point(x, y), confidence=1.0)]

        all_matches = []
        screen = self._driver.capture()
        for variant in element.variants or []:
            matches = self._locate_variant(variant, screen, element.target)
            if matches and not element.find_all:
                return matches
            all_matches.extend(matches)

        if all_matches:
            if element.match_sort is MatchSort.XY_POSITION:
                all_matches.sort(key=lambda m: m.target.y + m.target.x)
            elif element.match_sort is MatchSort.CONFIDENCE:
                all_matches.sort(key=lambda m: m.confidence, reverse=True)

        return all_matches

    def _locate_variant(self, variant, screen, target):
        matches = []

        if isinstance(variant, ImageVariant):
            image = variant.load().image

            if not isinstance(target, (tuple, list)):
                target_name = target or variant.default_target
                for target_ in variant.targets or []:
                    if target_.name == target_name:
                        target = target_.model_copy()
                        break
            else:
                target = Target(name="", x=target[0], y=target[1])

            if variant.match_area:
                y_start = variant.match_area.top
                y_end = variant.match_area.bottom
                x_start = variant.match_area.left
                x_end = variant.match_area.right
                image = image[y_start:y_end, x_start:x_end]

                if target:
                    target.x -= x_start
                    target.y -= y_start

            search_area = to_area(variant.search_area, screen)

            for detection, detector in DETECTORS.items():
                if getattr(variant, f"use_{detection}"):
                    matches = detector().locate(
                        image,
                        screen,
                        target=None if not target else [target.x, target.y],
                        area=search_area.as_xywh() if search_area else None,
                        match_sort=variant.match_sort,
                        limit=-1,
                        params={
                            k.removeprefix(f"{detection}_"): v
                            for k, v in variant.to_dict().items()
                            if k.startswith(f"{detection}_")
                        },
                    )
                    if matches:
                        return matches

        if isinstance(variant, TextVariant):
            search_area = to_area(variant.search_area, screen)

            matches = Ocr().locate_text_on_image(
                screen,
                variant.text,
                variant.text_fidelity,
                variant.text_confidence_threshold,
                area=search_area.as_xywh() if search_area else None,
            )
            matches = Ocr.sort(matches, variant.match_sort)

        return matches

    def _wait(self, *, on: Elements = None, off: Elements = None) -> WaitResult:
        if isinstance(on, Element):
            on = [on]
        if isinstance(off, Element):
            off = [off]

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
        start = time.time()
        suspended_at_start = self._driver.suspended_time
        assert element.timeout is not None
        assert element.match_index is not None
        while (current := time.time() - start - (self._driver.suspended_time - suspended_at_start)) < element.timeout:
            matches = self._locate_element(element=element)
            if on_screen and matches:
                try:
                    return True, current, matches[element.match_index]
                except IndexError:
                    length = len(matches)
                    raise Exception(
                        f"Cannot reach match index [{element.match_index}] for Element {element.name}. "
                        f"Valid range is [0-{length - 1}] ({length} matches found)."
                    )
            if not on_screen and not matches:
                return True, current, None
            sleep_(min(POLL_INTERVAL, element.timeout - current))
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
