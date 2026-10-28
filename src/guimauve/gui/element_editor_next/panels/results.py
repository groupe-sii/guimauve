"""What the results of a test say: a summary and rows, built from a TestResult without any widget."""

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from guimauve.enums import MatchSort
from guimauve.gui.element_editor_next.state import TestResult, TestScope
from guimauve.models.variant import ImageVariant, TextVariant, Variant

if TYPE_CHECKING:  # the detection loads the OCR models
    from guimauve.detection.locate import LocateReport, VariantReport

METHODS = {"template": "Template", "feature": "Feature", "ocr": "OCR"}
TRIED = {"template": "template matching", "feature": "feature matching", "ocr": "OCR"}
SORTS = {
    MatchSort.CONFIDENCE: "best score first",
    MatchSort.TOP_LEFT: "top left first",
    MatchSort.TOP_RIGHT: "top right first",
    MatchSort.BOTTOM_LEFT: "bottom left first",
    MatchSort.BOTTOM_RIGHT: "bottom right first",
}
NOT_TESTED = "Press Run test (F5) to search the element on the capture."
STALE = "Out of date · Run test (F5)"
FOUND, NOT_FOUND, SKIPPED, USED, MATCH = "Found", "Not found", "Skipped", "Used", "Match"


@dataclass(frozen=True)
class Row:
    """A line of the table: a match, or for the element a variant with its matches under it.

    :param number: Number of the match, as on the full screen; None for a variant.
    :param match: Index of the match in the report; None for a variant.
    """

    variant: str = ""
    number: int | None = None
    method: str = ""
    score: str = ""
    score_tip: str = ""
    position: str = ""
    screen: str = ""
    status: str = ""
    status_tip: str = ""
    used: bool = False
    match: int | None = None
    children: tuple["Row", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Summary:
    """Line above the table, an error or warnings under it, and whether the table lists screens."""

    text: str
    error: str | None = None
    warnings: tuple[str, ...] = ()
    screens: bool = False


def score_text(score: float) -> str:
    """Score cut to two decimals, never above the score: 0.879 shows 0.87, not 0.88."""
    return f"{math.floor(score * 100 + 1e-9) / 100:.2f}"


def summary(result: TestResult) -> Summary:
    """What the test searched, what it found, how the matches are sorted and how long it took."""
    report = result.report
    parts = [_scope(result)]
    if report is not None and report.fixed_position:
        match = report.matches[0]
        parts.append(f"Fixed position · click at {match.target.x}, {match.target.y}")
    elif report is not None:
        parts.extend(_outcome(result, report))
    parts.append(f"{round(result.duration * 1000)} ms")
    if not result.include_code:
        parts.append("without code overrides")
    warnings = tuple(_unfit(report)) if report is not None else ()
    screens = report is not None and len(set(report.match_screens)) > 1
    return Summary(" · ".join(parts), result.error, warnings, screens)


def rows(result: TestResult) -> list[Row]:
    """Matches of a variant; for the element, each variant with its matches under it."""
    report = result.report
    if report is None or report.fixed_position:
        return []
    if result.scope is TestScope.VARIANT:
        return [_match_row(result, report, index) for index in range(len(report.matches))]
    return [_variant_row(result, report, index, variant) for index, variant in enumerate(report.variants)]


def found_variant(result: TestResult) -> int | None:
    """Index in the element searched of the variant whose match a run would use, if any."""
    report = result.report
    if report is None or result.used is None or report.fixed_position:
        return None
    return report.match_variants[result.used]


def tried(variant: Variant) -> list[str]:
    """Detection methods a variant searches with, in the order they are tried."""
    if isinstance(variant, TextVariant):
        return ["ocr"]
    if isinstance(variant, ImageVariant):
        return [method for method in METHODS if getattr(variant, f"use_{method}")]
    return []


def _scope(result: TestResult) -> str:
    report = result.report
    if result.scope is TestScope.ELEMENT or report is None or not report.variants:
        return "Element" if result.scope is TestScope.ELEMENT else "Variant"
    return f"Variant {report.variants[0].variant.name}"


def _outcome(result: TestResult, report: "LocateReport") -> list[str]:
    if not report.matches:
        return [NOT_FOUND]
    index = found_variant(result)
    if result.scope is TestScope.ELEMENT and index is not None:
        found = f"{FOUND} with {report.variants[index].variant.name}"
    else:
        found = FOUND
    count = len(report.matches)
    return [found, f"{count} {'match' if count == 1 else 'matches'}", _sort(result, report)]


def _sort(result: TestResult, report: "LocateReport") -> str:
    element = result.element
    if element is not None and element.find_all:
        sort = element.match_sort
    else:
        sort = report.variants[report.match_variants[0]].variant.match_sort if report.match_variants else None
    text = SORTS.get(sort, "") if sort is not None else ""
    if 0 in report.match_screens:
        return f"{text} on the desktop" if sort is not MatchSort.CONFIDENCE else text
    return f"{text} on each screen" if len(set(report.match_screens)) > 1 else text


def _unfit(report: "LocateReport") -> list[str]:
    return [
        f"{variant.variant.name}: image larger than the search area on screen {screen}"
        for variant in report.variants
        for screen in variant.unfit_screens
    ]


def _match_row(result: TestResult, report: "LocateReport", index: int) -> Row:
    match = report.matches[index]
    variant = report.variants[report.match_variants[index]] if report.match_variants else None
    return Row(
        number=index + 1,
        method=METHODS.get(variant.method or "", "") if variant is not None else "",
        score=score_text(match.confidence),
        score_tip=f"{match.confidence:.4f}",
        position=f"{match.target.x}, {match.target.y}",
        screen=str(report.match_screens[index]) if report.match_screens else "",
        status=USED if index == result.used else MATCH,
        used=index == result.used,
        match=index,
    )


def _variant_row(result: TestResult, report: "LocateReport", index: int, variant: "VariantReport") -> Row:
    matches = tuple(
        _match_row(result, report, number) for number, owner in enumerate(report.match_variants) if owner == index
    )
    if variant.status.name == "SKIPPED":  # VariantStatus, not imported: the detection loads the OCR
        status, tip = SKIPPED, "An earlier variant was found"
    elif matches:
        status, tip = FOUND, ""
    else:
        names = [TRIED[method] for method in tried(variant.variant)]
        status, tip = NOT_FOUND, f"Not found · tried {_listed(names)}" if names else ""
    return Row(
        variant=f"{index + 1} · {variant.variant.name}",
        method=METHODS.get(variant.method or "", "") if matches else "",
        status=status,
        status_tip=tip,
        children=matches,
    )


def _listed(words: list[str]) -> str:
    """Words joined as in a sentence: "a", "a and b", "a, b and c"."""
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"
