from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np

from guimauve.detection.detector import Box, Match, Point
from guimauve.detection.feature_matching import FeatureMatching
from guimauve.detection.ocr import Ocr
from guimauve.detection.template_matching import TemplateMatching
from guimauve.drivers.driver import Screen
from guimauve.enums import MatchSort, OcrFidelity, ScreenArea
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, Target, TextVariant, Variant

DETECTORS: dict[str, type[TemplateMatching] | type[FeatureMatching] | type[Ocr]] = {
    "template": TemplateMatching,
    "feature": FeatureMatching,
    "ocr": Ocr,
}

TargetSpec = str | tuple[int, int] | list[int] | None


class VariantStatus(Enum):
    FOUND = auto()
    NOT_FOUND = auto()
    SKIPPED = auto()


@dataclass(frozen=True)
class VariantReport:
    """Outcome of the search for one variant."""

    variant: Variant
    status: VariantStatus
    method: str | None = None
    matches: list[Match] = field(default_factory=list)
    unfit_screens: list[int] = field(default_factory=list)  # skipped: the image is larger than their search area


@dataclass(frozen=True)
class LocateReport:
    """Outcome of the search for an element."""

    matches: list[Match]
    variants: list[VariantReport] = field(default_factory=list)
    fixed_position: bool = False

    @property
    def found(self) -> bool:
        return bool(self.matches)


def to_area(screen_area: Area | ScreenArea | None, image: np.ndarray, screen: int | None = None) -> Area | None:
    """Converts a screen area to an absolute area sized from the given image, and checks it fits in that image.

    :param screen_area: Area to convert, relative to the image.
    :param image: Image the area applies to.
    :param screen: Number of the screen the image comes from, used in the error message.
    :return: The absolute area, or None when no area is given.
    :raises ValueError: If the area exceeds the image.
    """
    h, w, _ = image.shape
    if isinstance(screen_area, ScreenArea):
        return screen_area.get_area((w, h))
    if screen_area and (screen_area.right > w or screen_area.bottom > h):
        where = f"screen {screen}: {w}x{h}" if screen is not None else f"the screen size {w}x{h}"
        raise ValueError(f"Area {screen_area.as_ltrb()} exceeds {where}")
    return screen_area


def screens_to_search(screen: int | list[int] | None, screens: list[Screen]) -> list[int]:
    """Lists the screens to search, in order.

    :param screen: Screen number or list of screen numbers; None means the primary screen.
    :param screens: Screens listed by the driver; empty when the driver cannot list them (VNC).
    :return: The screen numbers to search; a single one when the driver cannot list screens.
    """
    wanted = screen if isinstance(screen, list) else [1 if screen is None else screen]
    return wanted if screens else wanted[:1]


def screen_origin(screen: int, screens: list[Screen]) -> tuple[int, int]:
    """Gives the desktop position of a screen's top-left corner.

    :param screen: Screen number.
    :param screens: Screens listed by the driver; empty when the driver cannot list them (VNC).
    :return: The (left, top) position, (0, 0) when the driver cannot list screens.
    :raises ValueError: If the screen does not exist.
    """
    if not screens:
        return 0, 0
    if not 0 <= screen < len(screens):
        raise ValueError(f"Screen {screen} does not exist: {len(screens) - 1} screens available")
    return screens[screen].left, screens[screen].top


def locate_element(
    element: Element, grab: Callable[[int], np.ndarray], screens: list[Screen], mouse_position: tuple[int, int]
) -> LocateReport:
    """Locates a resolved element on its screens, in desktop coordinates.

    A fixed position is relative to the first screen searched and needs no capture. Otherwise each variant is searched
    on each screen, variant by variant, stopping at the first match unless ``find_all`` is set, in which case all
    matches are merged and sorted.

    :param element: Element whose settings are merged with the element and default values.
    :param grab: Captures a screen by its number; each screen is captured at most once.
    :param screens: Screens listed by the driver; empty when the driver cannot list them (VNC).
    :param mouse_position: Current mouse position, for positions relative to the mouse.
    :return: The matches in desktop coordinates, with the outcome of each variant.
    """
    to_search = screens_to_search(element.screen, screens)

    if element.has_coordinates():
        left, top = screen_origin(to_search[0], screens)
        x, y = element.resolve_coordinates(*mouse_position)
        x += left if element.x is not None else 0
        y += top if element.y is not None else 0
        return LocateReport(matches=[Match(box=None, target=Point(x, y), confidence=1.0)], fixed_position=True)

    images: dict[int, np.ndarray] = {}

    def image_of(screen: int) -> np.ndarray:
        if screen not in images:
            images[screen] = grab(screen)
        return images[screen]

    variants = list(element.variants or [])
    reports: list[VariantReport] = []
    all_matches: list[Match] = []

    for index, variant in enumerate(variants):
        report = _locate_on_screens(variant, image_of, to_search, screens, element.target, element.find_all)
        reports.append(report)
        if report.matches and not element.find_all:
            reports.extend(VariantReport(v, VariantStatus.SKIPPED) for v in variants[index + 1 :])
            return LocateReport(matches=report.matches, variants=reports)
        all_matches.extend(report.matches)

    return LocateReport(matches=_sort(all_matches, element.match_sort), variants=reports)


def locate_text(
    text: str,
    grab: Callable[[int], np.ndarray],
    screens: list[Screen],
    screen: int | list[int] | None,
    screen_area: Area | ScreenArea | None,
    fidelity: OcrFidelity,
    confidence_threshold: float,
) -> list[Match]:
    """Locates a text on each screen to search.

    :param text: Text to find.
    :param grab: Captures a screen by its number.
    :param screens: Screens listed by the driver; empty when the driver cannot list them (VNC).
    :param screen: Screen number or list of screen numbers to search.
    :param screen_area: Area to search, applied to each screen.
    :param fidelity: OCR fidelity.
    :param confidence_threshold: Minimum OCR confidence.
    :return: Every occurrence, in desktop coordinates.
    """
    matches: list[Match] = []
    for number in screens_to_search(screen, screens):
        image = grab(number)
        area = to_area(screen_area, image, number)
        found = Ocr().locate_text_on_image(
            image, text, fidelity, confidence_threshold, area=area.as_xywh() if area else None
        )
        matches.extend(_to_desktop(found, number, screens))
    return matches


def locate_variant(variant: Variant, image: np.ndarray, target: TargetSpec) -> VariantReport:
    """Locates a resolved variant on one image.

    Image variants try their enabled detection methods in ``DETECTORS`` order; the first one that finds something
    wins. Text variants are searched with OCR.

    :param variant: Variant whose settings are merged with the element and default values.
    :param image: Image to search.
    :param target: Target to click: its name, its coordinates in the variant image, or None for the default one.
    :return: The outcome of the search, with matches in image coordinates.
    """
    if isinstance(variant, ImageVariant):
        return _locate_image(variant, image, target)
    if isinstance(variant, TextVariant):
        return _locate_text(variant, image)
    return VariantReport(variant, VariantStatus.NOT_FOUND)


def _locate_on_screens(
    variant: Variant,
    image_of: Callable[[int], np.ndarray],
    to_search: list[int],
    screens: list[Screen],
    target: TargetSpec,
    find_all: bool | None,
) -> VariantReport:
    """Searches one variant on each screen, in order, and merges what it finds in desktop coordinates.

    :param variant: Variant to search.
    :param image_of: Gives the image of a screen, captured once.
    :param to_search: Screen numbers to search, in order.
    :param screens: Screens listed by the driver.
    :param target: Target to click.
    :param find_all: Whether to search every screen instead of stopping at the first match.
    :return: The outcome of the search, with the screens skipped because the image does not fit.
    """
    method: str | None = None
    matches: list[Match] = []
    unfit: list[int] = []
    for screen in to_search:
        image = image_of(screen)
        if not _fits(variant, image, screen):
            unfit.append(screen)
            continue
        report = locate_variant(variant, image, target)
        found = _to_desktop(report.matches, screen, screens)
        if found:
            method = method or report.method
            matches.extend(found)
            if not find_all:
                break
    status = VariantStatus.FOUND if matches else VariantStatus.NOT_FOUND
    return VariantReport(variant, status, method, matches, unfit)


def _fits(variant: Variant, image: np.ndarray, screen: int) -> bool:
    """Checks whether the image of an image variant fits in the search area of a screen; text always fits.

    :param variant: Variant to check.
    :param image: Image of the screen.
    :param screen: Number of the screen, used in error messages.
    :return: True if the variant image fits in the search area.
    """
    if not isinstance(variant, ImageVariant):
        return True
    needle, _ = _crop_to_match_area(variant, variant.load().image, None)
    area = to_area(variant.search_area, image, screen)
    height, width = (area.height, area.width) if area else image.shape[:2]
    return needle.shape[0] <= height and needle.shape[1] <= width


def _to_desktop(matches: list[Match], screen: int, screens: list[Screen]) -> list[Match]:
    """Moves matches found on the image of a screen to desktop coordinates.

    On the image of all screens (0), matches in the gaps between screens are dropped.

    :param matches: Matches in image coordinates.
    :param screen: Number of the screen the image comes from.
    :param screens: Screens listed by the driver.
    :return: The matches in desktop coordinates.
    """
    left, top = screen_origin(screen, screens)
    moved = [_shift(match, left, top) for match in matches]
    if screen == 0 and screens:
        moved = [m for m in moved if any(_contains(s, m.target) for s in screens[1:])]
    return moved


def _shift(match: Match, dx: int, dy: int) -> Match:
    box = None if match.box is None else Box(*(Point(p.x + dx, p.y + dy) for p in match.box))
    return Match(box=box, target=Point(match.target.x + dx, match.target.y + dy), confidence=match.confidence)


def _contains(screen: Screen, point: Point) -> bool:
    return screen.left <= point.x < screen.left + screen.width and screen.top <= point.y < screen.top + screen.height


def _locate_image(variant: ImageVariant, image: np.ndarray, target: TargetSpec) -> VariantReport:
    needle = variant.load().image
    resolved = _resolve_target(variant, target)
    needle, resolved = _crop_to_match_area(variant, needle, resolved)
    search_area = to_area(variant.search_area, image)

    for detection, detector in DETECTORS.items():
        if not getattr(variant, f"use_{detection}"):
            continue
        matches = detector().locate(
            needle,
            image,
            target=None if not resolved else [resolved.x, resolved.y],
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
            return VariantReport(variant, VariantStatus.FOUND, detection, matches)

    return VariantReport(variant, VariantStatus.NOT_FOUND)


def _locate_text(variant: TextVariant, image: np.ndarray) -> VariantReport:
    fidelity, threshold = variant.text_fidelity, variant.text_confidence_threshold
    if fidelity is None or threshold is None:
        raise ValueError(f"Text variant '{variant.name}' must be resolved before being located")

    search_area = to_area(variant.search_area, image)
    matches = Ocr().locate_text_on_image(
        image,
        variant.text,
        fidelity,
        threshold,
        area=search_area.as_xywh() if search_area else None,
    )
    matches = Ocr.sort(matches, variant.match_sort)
    status = VariantStatus.FOUND if matches else VariantStatus.NOT_FOUND
    return VariantReport(variant, status, "ocr", matches)


def _resolve_target(variant: ImageVariant, target: TargetSpec) -> Target | None:
    """Returns a copy of the target to click, in image coordinates, or None for the centre of the match."""
    if isinstance(target, (tuple, list)):
        return Target(name="", x=target[0], y=target[1])

    name = target or variant.default_target
    for candidate in variant.targets or []:
        if candidate.name == name:
            return candidate.model_copy()
    return None


def _crop_to_match_area(
    variant: ImageVariant, image: np.ndarray, target: Target | None
) -> tuple[np.ndarray, Target | None]:
    """Keeps only the match area of the image, and moves the target into the cropped image."""
    area = variant.match_area
    if not area:
        return image, target

    image = image[area.top : area.bottom, area.left : area.right]
    if target:
        target.x -= area.left
        target.y -= area.top
    return image, target


def _sort(matches: list[Match], match_sort: MatchSort | None) -> list[Match]:
    """Sorts the matches of several variants, as the controller always did."""
    if match_sort is MatchSort.XY_POSITION:
        matches.sort(key=lambda m: m.target.y + m.target.x)
    elif match_sort is MatchSort.CONFIDENCE:
        matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches
