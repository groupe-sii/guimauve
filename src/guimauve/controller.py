import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Iterable, Optional, Union

import cv2 as cv
import numpy as np
from sugar import UNDEFINED, SchemaValidationError

from guimauve.data_manager import DataManager
from guimauve.detection.detector import Match, Point
from guimauve.detection.feature_matching import FeatureMatching
from guimauve.detection.ocr import Ocr
from guimauve.detection.template_matching import TemplateMatching
from guimauve.drivers.local.driver import LocalDriver
from guimauve.drivers.vnc.driver import VNCDriver
from guimauve.enums import Button, Key, MatchSort, Menu, MouseDirection, OcrFidelity, ScreenArea
from guimauve.gui.element_editor import Context, start_element_editor
from guimauve.log_screenshot import log_screenshot
from guimauve.models.area import Area
from guimauve.models.data import Data
from guimauve.models.element import Element
from guimauve.models.parameters.parameters import Parameters
from guimauve.models.variant import ImageVariant, Target, TextVariant
from guimauve.pause_manager import PauseManager
from guimauve.utils.image import diff_area, similarity_index
from guimauve.utils.time import sleep as sleep_

logger = logging.getLogger(__name__)

DataType = Optional[Union[Data, Path, dict, str]]
IntervalType = Union[int, float]
ParametersType = Optional[Union[Parameters, Path, dict, str]]
SleepType = Optional[Union[int, float]]
Elements = Optional[Union[Element, Iterable[Element]]]

DETECTORS = {"template": TemplateMatching, "feature": FeatureMatching, "ocr": Ocr}
DRIVERS = {"local": LocalDriver, "vnc": VNCDriver}


def get_elements_kwargs(kwargs: dict) -> dict[str, list[Element]]:
    elements = {}
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
            is_initiator = False
            if self._root_action is None:
                self._root_action = func.__name__
                is_initiator = True

            self._check_pause()
            elements_params = get_elements_kwargs(kwargs)

            for param_name, element_list in elements_params.items():
                updated_list = []
                for element in element_list:
                    if not (element := self._trigger_editor_new_element(element)):
                        return None

                    if not (element := self._trigger_editor_element_not_valid(element)):
                        return None

                    if update_element:
                        element = self._update(element)

                    if use_wait:
                        if not (element := self._trigger_editor_element_not_found(element)):
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

            if is_initiator:
                self._root_action = None

            return result

        return wrapper

    return decorator


@dataclass
class ElementResult:
    success: bool
    time: Optional[float] = None
    match: Optional[Match] = None


@dataclass
class WaitResult:
    results: dict[str, ElementResult]

    def get(self, key: str) -> Optional[ElementResult]:
        return self.results.get(key)

    def __bool__(self):
        return all(res.success for res in self.results.values())


class Controller:
    def __init__(self, parameters: ParametersType = None):
        self.parameters = parameters
        if parameters is None:
            self.parameters = Parameters()
        elif isinstance(parameters, dict):
            self.parameters = Parameters.from_dict(parameters)
        elif isinstance(parameters, (Path, str)):
            self.parameters = Parameters.from_file(parameters)

        if errors := self.parameters.validate():
            raise SchemaValidationError(errors, context="parameters")

        params = {}
        if self.parameters.execution_mode == "vnc":
            params = self.parameters.vnc.to_dict()

        self._driver = DRIVERS[self.parameters.execution_mode](**params)
        self._pause_manager = PauseManager(self.parameters.pause_shortcut)
        self._root_action = None

    @handle_action(sleep_after=False, use_wait=False)
    def locate(self, element: Optional[Element] = None) -> list[Match]:
        return self._locate_element(element=element)

    @handle_action(sleep_after=False, use_wait=False)
    def wait(self, *, on: Elements = None, off: Elements = None) -> WaitResult:
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

    @handle_action()
    def move(self, *, on: Element = None, sleep: SleepType = None) -> None:
        if on is None:
            return

        end = self._locate_element(element=on)[0].target
        if not on.mouse_speed:
            self._driver.mouse_move(*end)
            return

        start = self.mouse_position
        positions = {
            MouseDirection.STRAIGHT: [[start, end]],
            MouseDirection.XY_X: [[start, (end.x, start.y)], [(end.x, start.y), end]],
            MouseDirection.XY_Y: [[start, (start.x, end.y)], [(start.x, end.y), end]],
        }

        for start, end in positions.get(on.mouse_direction, []):
            self._move(start, end, on.mouse_speed)

    @handle_action()
    def click(
        self, *, on: Element = None, button: Button = Button.LEFT, count: int = 1, sleep: SleepType = None
    ) -> None:
        if on:
            self.move(on=on)

        for i in range(count):
            self._driver.mouse_down(button)
            self._driver.mouse_up(button)

    @handle_action()
    def double_click(self, *, on: Element = None, button: Button = Button.LEFT, sleep: SleepType = None) -> None:
        self.click(on=on, button=button, count=2)

    @handle_action()
    def triple_click(self, *, on: Element = None, button: Button = Button.LEFT, sleep: SleepType = None) -> None:
        self.click(on=on, button=button, count=3)

    @handle_action()
    def right_click(self, *, on: Element = None, sleep: SleepType = None) -> None:
        self.click(on=on, button=Button.RIGHT, count=1)

    @handle_action()
    def scroll(self, *, v: int = 0, h: int = 0, on: Element = None, sleep: SleepType = None) -> None:
        if on:
            self.move(on=on)
        self._driver.mouse_scroll(v, h)

    @handle_action()
    def drag(self, *, on: Element = None, button: Button = Button.LEFT, sleep: SleepType = None) -> None:
        self.down(button)
        if on:
            self.move(on=on)
        self.up(button)

    @handle_action(update_element=False, use_wait=False)
    def type(self, text: str, interval: IntervalType = 0, sleep: SleepType = None) -> None:
        if interval == 0:
            self._driver.paste(text)
            return

        for char in text:
            self._driver.type(char)
            self._check_pause()
            sleep_(interval)

    @handle_action(update_element=False, use_wait=False)
    def press(self, *keys: Key, interval: IntervalType = 0, sleep: SleepType = None) -> None:
        for key in keys:
            self._driver.key_down(key)
            sleep_(interval)
        for key in reversed(keys):
            self._driver.key_up(key)

    @handle_action(sleep_after=False, update_element=False, use_wait=False)
    def down(self, *args: Union[Key, Button]) -> None:
        for arg in args:
            if isinstance(arg, Key):
                self._driver.key_down(arg)
            elif isinstance(arg, Button):
                self._driver.mouse_down(arg)
            else:
                raise ValueError(f"Unsupported argument {type(arg)}, must be Key or Button")

    @handle_action(sleep_after=False, update_element=False, use_wait=False)
    def up(self, *args: Union[Key, Button]) -> None:
        for arg in args:
            if isinstance(arg, Key):
                self._driver.key_up(arg)
            elif isinstance(arg, Button):
                self._driver.mouse_up(arg)
            else:
                raise ValueError(f"Unsupported argument {type(arg)}, must be Key or Button")

    @handle_action(sleep_after=False, update_element=False, use_wait=False)
    @contextmanager
    def hold(self, *args: Union[Key, Button], sleep: SleepType = None):
        self.down(*args)
        try:
            yield
        finally:
            self.up(*args)

    @property
    def mouse_position(self) -> Point:
        return Point(*self._driver.mouse_position())

    @property
    def screen_size(self) -> tuple[int, int]:
        img = self._driver.capture()
        return img.shape[:2][::-1]

    def screenshot(
        self, screen_area: Optional[Union[Area, ScreenArea]] = None, path: Optional[Union[Path, str]] = None
    ) -> np.ndarray:
        screen = self._driver.capture()

        if screen_area:
            if isinstance(screen_area, ScreenArea):
                h, w, _ = screen.shape
                screen_area = screen_area.get_area((w, h))

            x, y, w, h = screen_area.as_xywh()
            screen = screen[y : y + h, x : x + w]

        if path:
            cv.imwrite(str(path), screen)

        return screen

    @handle_action(update_element=False, use_wait=False)
    def scroll_until(self, v: int = 0, h: int = 0, element: Element = None, sleep: SleepType = None) -> Optional[Match]:
        before, after = np.array([0]), np.array([1])
        while similarity_index(before, after) < 1:
            if element and (match := self.locate(element=element)):
                return match[0]

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
            overrides = {"mouse_direction": directions[menu.value if is_last else (idx + 1) % 2]}
            if search_area is not None:
                overrides["search_area"] = search_area

            before = after
            if is_last:
                self.click(on=element(**overrides))
            else:
                self.move(on=element(**overrides))

    def read_text(
        self, screen_area: Optional[Union[Area, ScreenArea]] = None, fidelity: OcrFidelity = OcrFidelity.ACCURATE
    ) -> str:
        return Ocr().read_text_on_image(self.screenshot(screen_area=screen_area), fidelity)

    def locate_text(
        self,
        text: str,
        screen_area: Optional[Union[Area, ScreenArea]] = None,
        fidelity: OcrFidelity = OcrFidelity.FAST,
        confidence_threshold: float = 0.8,
    ) -> list[Match]:
        screen = self._driver.capture()
        if screen_area:
            if isinstance(screen_area, ScreenArea):
                h, w, _ = screen.shape
                screen_area = screen_area.get_area((w, h))
        return Ocr().locate_text_on_image(
            screen,
            text,
            fidelity,
            confidence_threshold,
            area=screen_area.as_xywh() if screen_area else None,
        )

    def connect(self) -> None:
        """For remote modes that require starting a session."""
        if hasattr(self._driver, "connect"):
            self._driver.connect()

    def close(self) -> None:
        """For remote modes that require closing a session."""
        if hasattr(self._driver, "close"):
            self._driver.close()

    def replay(self):
        raise NotImplementedError

    def pixel_color(self, x, y):
        raise NotImplementedError

    def _locate_element(self, element: Optional[Element] = None) -> list[Match]:
        if element is None:
            return []

        if element.has_coordinates():
            x, y = element.resolve_coordinates(*self.mouse_position)
            return [Match(box=None, target=Point(x, y), confidence=1.0)]

        all_matches = []
        screen = self._driver.capture()
        image_dir = DataManager.get_data(element).image_dir
        for variant in element.variants:
            matches = self._locate_variant(variant, screen, element.target, image_dir)
            if matches and not element.find_all:
                return matches
            all_matches.extend(matches)

        if all_matches:
            if element.match_sort is MatchSort.XY_POSITION:
                all_matches.sort(key=lambda m: m.target.y + m.target.x)
            elif element.match_sort is MatchSort.CONFIDENCE:
                all_matches.sort(key=lambda m: m.confidence, reverse=True)

        return all_matches

    def _locate_variant(self, variant, screen, target, image_dir):
        matches = []

        if isinstance(variant, ImageVariant):
            image = variant.image
            if image is UNDEFINED:
                raw_img = cv.imread(str(Path(image_dir) / variant.path))
                image = cv.cvtColor(raw_img, cv.COLOR_BGR2RGB)

            if not isinstance(target, (tuple, list)):
                target_name = target or variant.default_target
                for target_ in variant.targets or []:
                    if target_.name == target_name:
                        target = target_
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

            search_area = variant.search_area
            if isinstance(search_area, ScreenArea):
                h, w, _ = screen.shape
                search_area = search_area.get_area((w, h))

            for detection, detector in DETECTORS.items():
                if getattr(variant, f"use_{detection}"):
                    matches = detector().locate(
                        image,
                        screen,
                        target=None if not target else [target.x, target.y],
                        area=search_area.as_xywh(),
                        match_sort=variant.match_sort,
                        limit=-1,
                        params={
                            k.removeprefix(f"{detection}_"): v
                            for k, v in variant.to_dict(serializable=False).items()
                            if k.startswith(f"{detection}_")
                        },
                    )
                    if matches:
                        return matches

        if isinstance(variant, TextVariant):
            search_area = variant.search_area
            if isinstance(search_area, ScreenArea):
                h, w, _ = screen.shape
                search_area = search_area.get_area((w, h))

            matches = Ocr().locate_text_on_image(
                screen,
                variant.text,
                variant.text_fidelity,
                variant.text_confidence_threshold,
                area=search_area.as_xywh() if search_area else None,
            )
            matches = Ocr.sort(matches, variant.match_sort)

        return matches

    def _check_pause(self) -> None:
        if self._pause_manager.is_paused():
            logger.info("Controller paused")
            self._pause_manager.wait_while_paused()
            logger.info("Controller resumed")

    def _check_element(self, element: Element, on_screen: bool) -> tuple[bool, Optional[float], Optional[Match]]:
        start = time.time()
        while (current := time.time() - start) < element.timeout:
            matches = self.locate(element=element)
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
        return False, None, None

    def _move(self, start: tuple[int, int], end: tuple[int, int], speed: Union[float, int]):
        start_x, start_y = start
        end_x, end_y = end

        distance = math.hypot(end_x - start_x, end_y - start_y)
        if distance == 0:
            return

        duration = distance / speed
        steps = min(max(int(distance), 1), 100)
        interval = duration / steps

        for step in range(steps + 1):
            self._check_pause()
            t = step / steps
            new_x = int(start_x + (end_x - start_x) * t)
            new_y = int(start_y + (end_y - start_y) * t)
            self._driver.mouse_move(new_x, new_y)
            sleep_(interval)

    def _update(self, element: Element):
        element = element.update_from(self.parameters.default, overwrite=False)
        element.variants = [variant.update_from(element, overwrite=False) for variant in element.variants or []]
        return element

    def _trigger_editor(self, element: Element, message: str) -> Optional[Element]:
        element, to_save = start_element_editor(
            Context(
                element=element,
                default=self.parameters.default,
                image_dir=DataManager.get_data(element).image_dir,
                capture_provider=self._driver.capture,
                message=message,
                action=self._root_action or "manual_call",
            )
        )
        if not to_save:
            return None

        element._is_new = False
        DataManager.save_element(element)
        return element

    def _trigger_editor_new_element(self, element: Element) -> Optional[Element]:
        if element._is_new:
            if not self.parameters.debug_elements:
                raise Exception(f"Element {element.name} is not defined")

            element = self._trigger_editor(element, "ELEMENT NOT DEFINED")
        return element

    def _trigger_editor_element_not_valid(self, element: Element) -> Optional[Element]:
        while errors := element.validate():
            if not self.parameters.debug_elements or not element.data_file:
                raise SchemaValidationError(errors, context=f"Element {element.name}")

            element = DataManager.get_element(element)
            element = self._trigger_editor(element, "INVALID ELEMENT")
            if not element:
                return None
            element = self._update(element)

        return element

    def _trigger_editor_element_not_found(self, element: Element) -> Optional[Element]:
        while not (wait_result := self.wait(on=element)):
            if not self.parameters.debug_elements or not element.data_file:
                raise Exception(f"Element {element.name} not found on screen")

            element = DataManager.get_element(element)
            element = self._trigger_editor(element, "ELEMENT NOT FOUND ON SCREEN")
            if not element:
                return None
            element = self._update(element)

        x, y = wait_result.get(element.name).match.target
        element = element(x=x, y=y, rel_x=UNDEFINED, rel_y=UNDEFINED)
        return element
