import pytest

from guimauve.detection.detector import Match, Point
from guimauve.detection.locate import LocateReport, VariantReport, VariantStatus
from guimauve.enums import MatchSort
from guimauve.gui.element_editor_next.panels.results import found_variant, rows, score_text, summary
from guimauve.gui.element_editor_next.state import TestResult, TestScope
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
