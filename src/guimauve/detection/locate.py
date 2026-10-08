from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np

from guimauve.detection.detector import Match, Point
from guimauve.detection.feature_matching import FeatureMatching
from guimauve.detection.ocr import Ocr
from guimauve.detection.template_matching import TemplateMatching
from guimauve.enums import MatchSort, ScreenArea
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


@dataclass(frozen=True)
class LocateReport:
    """Outcome of the search for an element."""

    matches: list[Match]
    variants: list[VariantReport] = field(default_factory=list)
    fixed_position: bool = False

    @property
    def found(self) -> bool:
        return bool(self.matches)


def to_area(screen_area: Area | ScreenArea | None, screen: np.ndarray) -> Area | None:
    """Converts a screen area to an absolute Area sized from the given screen, and checks it fits in that screen."""
    h, w, _ = screen.shape
    if isinstance(screen_area, ScreenArea):
        return screen_area.get_area((w, h))
    if screen_area and (screen_area.right > w or screen_area.bottom > h):
        raise ValueError(f"Area {screen_area.as_ltrb()} exceeds the screen size {w}x{h}")
    return screen_area


def locate_element(element: Element, screen: np.ndarray | None, mouse_position: tuple[int, int]) -> LocateReport:
    """Locates a resolved element on the screen.

    ``screen`` may be None for an element with a fixed position, which needs no capture.

    A fixed position skips detection. Otherwise variants are searched in order, stopping at the first
    one found unless ``find_all`` is set, in which case every variant is searched and all matches sorted.
    """
    if element.has_coordinates():
        x, y = element.resolve_coordinates(*mouse_position)
        return LocateReport(matches=[Match(box=None, target=Point(x, y), confidence=1.0)], fixed_position=True)

    if screen is None:
        raise ValueError("A screen is required to locate an element without a fixed position")

    variants = list(element.variants or [])
    reports: list[VariantReport] = []
    all_matches: list[Match] = []

    for index, variant in enumerate(variants):
        report = locate_variant(variant, screen, element.target)
        reports.append(report)
        if report.matches and not element.find_all:
            reports.extend(VariantReport(v, VariantStatus.SKIPPED) for v in variants[index + 1 :])
            return LocateReport(matches=report.matches, variants=reports)
        all_matches.extend(report.matches)

    return LocateReport(matches=_sort(all_matches, element.match_sort), variants=reports)


def locate_variant(variant: Variant, screen: np.ndarray, target: TargetSpec) -> VariantReport:
    """Locates a resolved variant on the screen.

    Image variants try their enabled detection methods in ``DETECTORS`` order; the first one that
    finds something wins. Text variants are searched with OCR.
    """
    if isinstance(variant, ImageVariant):
        return _locate_image(variant, screen, target)
    if isinstance(variant, TextVariant):
        return _locate_text(variant, screen)
    return VariantReport(variant, VariantStatus.NOT_FOUND)


def _locate_image(variant: ImageVariant, screen: np.ndarray, target: TargetSpec) -> VariantReport:
    image = variant.load().image
    resolved = _resolve_target(variant, target)
    image, resolved = _crop_to_match_area(variant, image, resolved)
    search_area = to_area(variant.search_area, screen)

    for detection, detector in DETECTORS.items():
        if not getattr(variant, f"use_{detection}"):
            continue
        matches = detector().locate(
            image,
            screen,
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


def _locate_text(variant: TextVariant, screen: np.ndarray) -> VariantReport:
    fidelity, threshold = variant.text_fidelity, variant.text_confidence_threshold
    if fidelity is None or threshold is None:
        raise ValueError(f"Text variant '{variant.name}' must be resolved before being located")

    search_area = to_area(variant.search_area, screen)
    matches = Ocr().locate_text_on_image(
        screen,
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
