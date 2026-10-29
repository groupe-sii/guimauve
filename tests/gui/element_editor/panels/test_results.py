import numpy as np
import pytest

from guimauve.detection.detector import Box, Match, Point
from guimauve.detection.locate import LocateReport, VariantReport, VariantStatus
from guimauve.drivers.driver import Screen
from guimauve.enums import MatchSort
from guimauve.gui.element_editor_next.panels.results import (
    found_variant,
    preview,
    rows,
    score_text,
    screen_views,
    summary,
)
from guimauve.gui.element_editor_next.state import TestResult, TestScope
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, TextVariant

LIGHT = ImageVariant(name="LIGHT", use_template=True, use_feature=True, use_ocr=False, match_sort=MatchSort.TOP_LEFT)
DARK = ImageVariant(name="DARK", use_template=True, use_feature=False, use_ocr=False, match_sort=MatchSort.TOP_LEFT)
LABEL = TextVariant(name="LABEL", text="Sign in")


def match(x: int, y: int, score: float = 0.9) -> Match:
    return Match(None, Point(x, y), score)


def result(report, scope=TestScope.VARIANT, used=0, **fields) -> TestResult:
    return TestResult(scope, 1, report, used=used, duration=0.084, **fields)


@pytest.mark.parametrize(("score", "text"), [(0.879, "0.87"), (0.88, "0.88"), (1.0, "1.00"), (0.8799999, "0.87")])
def test_scores_are_cut_never_rounded_up(score, text):
    assert score_text(score) == text


def test_variant_found():
    report = LocateReport(
        [match(10, 20, 0.94), match(10, 80, 0.901)],
        [VariantReport(LIGHT, VariantStatus.FOUND, "template", [], match_screens=[1, 1])],
        match_screens=[1, 1],
        match_variants=[0, 0],
    )

    said = summary(result(report))
    listed = rows(result(report))

    assert said.text == "Variant LIGHT · Found · 2 matches · top left first · 84 ms"
    assert not said.screens
    assert [(r.number, r.method, r.score, r.position, r.status) for r in listed] == [
        (1, "Template", "0.94", "10, 20", "Used"),
        (2, "Template", "0.90", "10, 80", "Match"),
    ]


def test_variant_not_found_without_code():
    report = LocateReport([], [VariantReport(LIGHT, VariantStatus.NOT_FOUND)])

    said = summary(result(report, used=None, include_code=False))

    assert said.text == "Variant LIGHT · Not found · 84 ms · without code overrides"
    assert rows(result(report, used=None)) == []


def test_matches_on_several_screens_are_sorted_on_each_and_list_their_screen():
    report = LocateReport(
        [match(1930, 10), match(10, 10)],
        [VariantReport(LIGHT, VariantStatus.FOUND, "feature", [])],
        match_screens=[2, 1],
        match_variants=[0, 0],
    )

    said = summary(result(report))

    assert "top left first on each screen" in said.text and said.screens
    assert [row.screen for row in rows(result(report))] == ["2", "1"]


def test_element_lists_each_variant_with_its_matches():
    report = LocateReport(
        [match(10, 20), match(10, 80)],
        [
            VariantReport(LIGHT, VariantStatus.NOT_FOUND),
            VariantReport(DARK, VariantStatus.FOUND, "template", []),
            VariantReport(LABEL, VariantStatus.SKIPPED),
        ],
        match_screens=[1, 1],
        match_variants=[1, 1],
    )
    tested = result(report, TestScope.ELEMENT, element=Element(name="button", find_all=False))

    listed = rows(tested)

    assert summary(tested).text.startswith("Element · Found with DARK · 2 matches")
    assert found_variant(tested) == 1
    assert [(row.variant, row.status) for row in listed] == [
        ("1 · LIGHT", "Not found"),
        ("2 · DARK", "Found"),
        ("3 · LABEL", "Skipped"),
    ]
    assert listed[0].method == "" and listed[0].status_tip == "Not found · tried template matching and feature matching"
    assert [(child.number, child.status) for child in listed[1].children] == [(1, "Used"), (2, "Match")]


def test_find_all_sorts_with_the_element():
    report = LocateReport(
        [match(10, 20, 0.95)],
        [VariantReport(LIGHT, VariantStatus.FOUND, "template", [])],
        match_screens=[0],
        match_variants=[0],
    )

    tested = result(report, element=Element(name="button", find_all=True, match_sort=MatchSort.BOTTOM_RIGHT))

    assert "bottom right first on the desktop" in summary(tested).text


def test_fixed_position():
    report = LocateReport([match(812, 455, 1.0)], fixed_position=True)

    said = summary(result(report))

    assert said.text == "Variant · Fixed position · click at 812, 455 · 84 ms"
    assert rows(result(report)) == [] and found_variant(result(report)) is None


def test_errors_and_unfit_screens():
    report = LocateReport(
        [match(1, 1), match(2, 2)],
        [VariantReport(LIGHT, VariantStatus.FOUND, "template", [], unfit_screens=[2])],
        match_screens=[1, 1],
        match_variants=[0, 0],
    )

    said = summary(result(report, used=None, error="Index 3 out of 2 matches"))

    assert said.error == "Index 3 out of 2 matches"
    assert said.warnings == ("LIGHT: image larger than the search area on screen 2",)


def capture(width: int, height: int, value: int = 0) -> np.ndarray:
    return np.full((height, width, 3), value, np.uint8)


def boxed(left: int, top: int, right: int, bottom: int, x: int, y: int) -> Match:
    corners = (Point(left, top), Point(right, top), Point(right, bottom), Point(left, bottom))
    return Match(Box(*corners), Point(x, y), 0.9)


def located(found: Match, screen: int) -> LocateReport:
    return LocateReport(
        [found], [VariantReport(LIGHT, VariantStatus.FOUND, "template", [])], match_screens=[screen], match_variants=[0]
    )


def test_preview_cuts_the_capture_around_the_match():
    report = located(boxed(40, 30, 60, 40, 50, 35), 1)
    tested = TestResult(TestScope.VARIANT, 1, report, {1: capture(200, 100)}, used=0)

    shown = preview(tested, 0, context=10)

    assert shown.image.shape[:2] == (30, 40)  # 10 + 20 + 10 wide, 10 + 10 + 10 high
    assert shown.box == ((10, 10), (30, 10), (30, 20), (10, 20)) and shown.target == (20, 15) and shown.used


def test_preview_on_another_screen_and_at_the_edge():
    screens = [Screen(-100, 0, 200, 100), Screen(0, 0, 100, 100), Screen(-100, 0, 100, 100)]
    report = located(boxed(-98, 2, -90, 8, -94, 5), 2)
    tested = TestResult(
        TestScope.VARIANT, 1, report, {1: capture(100, 100, 1), 2: capture(100, 100, 2)}, screens=screens
    )

    shown = preview(tested, 0, context=10)

    assert shown.image[0, 0, 0] == 2 and shown.image.shape[:2] == (26, 28)  # moved inside the screen, not cut
    assert shown.box[0] == (2, 2) and not shown.used


def test_preview_without_a_box_is_around_the_point():
    report = located(Match(None, Point(50, 50), 0.9), 1)
    tested = TestResult(TestScope.VARIANT, 1, report, {1: capture(100, 100)})

    shown = preview(tested, 0, context=10)

    assert shown.image.shape[:2] == (20, 20) and shown.box == () and shown.target == (10, 10)


def test_no_preview_without_the_capture():
    report = located(boxed(1, 1, 5, 5, 3, 3), 2)

    assert (
        preview(
            TestResult(TestScope.VARIANT, 1, report, {1: capture(10, 10)}, screens=[Screen(0, 0, 10, 10)] * 2), 0, 10
        )
        is None
    )


def test_preview_of_a_small_match_shows_more_around_it():
    report = located(boxed(190, 140, 210, 160, 200, 150), 1)
    tested = TestResult(TestScope.VARIANT, 1, report, {1: capture(400, 300)})

    shown = preview(tested, 0, context=10, least=(200, 120))

    assert shown.image.shape[:2] == (120, 200) and shown.target == (100, 60)  # centered


def test_preview_grown_near_an_edge_stays_in_the_capture():
    report = located(boxed(2, 2, 12, 12, 7, 7), 1)
    tested = TestResult(TestScope.VARIANT, 1, report, {1: capture(400, 300)})

    shown = preview(tested, 0, context=10, least=(200, 120))

    assert shown.image.shape[:2] == (120, 200) and shown.target == (7, 7)


DESKTOP = [Screen(-100, 0, 300, 100), Screen(0, 0, 200, 100), Screen(-100, 0, 100, 100)]


def views_of(report, screen, area=None, include_code=True, code=None, screens=DESKTOP):
    element = Element(name="button", screen=screen, search_area=area)
    captures = {1: capture(200, 100, 1), 2: capture(100, 100, 2)}
    tested = TestResult(TestScope.VARIANT, 1, report, captures, include_code, used=0, element=element, screens=screens)
    return {view.number: view for view in screen_views(tested, code)}


def test_views_of_one_screen_searched():
    report = located(boxed(10, 10, 30, 20, 20, 15), 1)

    views = views_of(report, 1, Area(left=5, top=5, right=50, bottom=40))

    assert views[1].searched and views[1].area == (5, 5, 50, 40)
    assert [(m.index, m.box[0], m.target, m.used) for m in views[1].matches] == [(0, (10, 10), (20, 15), True)]
    assert not views[2].searched and views[2].matches == ()


def test_views_of_the_desktop_move_its_area_and_matches_to_each_screen():
    report = located(boxed(-90, 10, -80, 20, -85, 15), 0)

    views = views_of(report, 0, Area(left=50, top=0, right=250, bottom=100))

    assert views[1].searched and views[2].searched
    assert views[1].area == (0, 0, 150, 100) and views[2].area == (50, 0, 100, 100)  # cut to each screen
    assert views[2].matches[0].target == (15, 15) and views[1].matches == ()


def test_code_area_shows_only_when_the_code_applied():
    report = located(boxed(1, 1, 5, 5, 3, 3), 1)
    code = Area(left=0, top=0, right=20, bottom=20)

    assert views_of(report, 1, code=code)[1].code_area == (0, 0, 20, 20)
    assert views_of(report, 1, include_code=False, code=code)[1].code_area is None


def test_a_single_capture_is_searched_whole():
    report = located(boxed(1, 1, 5, 5, 3, 3), 1)

    views = views_of(report, 3, screens=[])

    assert views[1].searched and views[1].area is None and len(views[1].matches) == 1


def test_a_fixed_position_shows_on_the_screen_under_it():
    report = LocateReport([Match(None, Point(-50, 40), 1.0)], fixed_position=True)

    views = views_of(report, 0)

    assert views[2].matches[0].target == (50, 40) and views[2].matches[0].box == ()
