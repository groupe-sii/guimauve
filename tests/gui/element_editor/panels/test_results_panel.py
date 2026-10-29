import numpy as np
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget

from guimauve.detection.detector import Box, Match, Point
from guimauve.detection.locate import LocateReport, VariantReport, VariantStatus
from guimauve.gui.element_editor_next.panels import ResultsPanel
from guimauve.gui.element_editor_next.panels.results_panel import HOVER_DELAY_MS, MATCH_ROLE, SCREEN, STATUS, VARIANT
from guimauve.gui.element_editor_next.state import ELEMENT, Mode, TestResult, TestScope
from guimauve.models.variant import ImageVariant

LIGHT = ImageVariant(name="LIGHT", use_template=True)


def found(scope=TestScope.VARIANT) -> TestResult:
    corners = (Point(4, 14), Point(16, 14), Point(16, 26), Point(4, 26))
    report = LocateReport(
        [Match(Box(*corners), Point(10, 20), 0.94), Match(None, Point(10, 80), 0.9)],
        [VariantReport(LIGHT, VariantStatus.FOUND, "template", [])],
        match_screens=[1, 1],
        match_variants=[0, 0],
    )
    captures = {1: np.full((100, 100, 3), 200, np.uint8)}
    return TestResult(scope, 1, report, captures, used=0, duration=0.01)


@pytest.fixture
def panel(store, theme, qtbot):
    parent = QWidget()  # shown, and the panel with it unless it hides itself
    qtbot.addWidget(parent)
    widget = ResultsPanel(store, theme, parent=parent)
    widget.resize(600, 300)
    parent.show()
    yield widget  # the parent lives as long as the test


def texts(panel) -> list[list[str]]:
    tree = panel.tree
    items = [tree.topLevelItem(index) for index in range(tree.topLevelItemCount())]
    every = [child for item in items for child in [item, *(item.child(n) for n in range(item.childCount()))]]
    return [[item.text(column) for column in range(tree.columnCount())] for item in every]


def test_shown_in_test_mode_only(store, panel):
    assert not panel.isVisible()

    store.set_mode(Mode.TEST)

    assert panel.isVisible() and panel.empty.isVisible() and not panel.tree.isVisible()


def test_lists_the_matches_of_a_variant(store, panel):
    store.set_mode(Mode.TEST)

    store.set_test_result(found())

    assert panel.summary.full_text().startswith("Variant LIGHT · Found · 2 matches")
    assert texts(panel) == [
        ["1", "", "Template", "0.94", "10, 20", "1", "Used"],
        ["2", "", "Template", "0.90", "10, 80", "1", "Match"],
    ]
    assert panel.tree.isColumnHidden(VARIANT) and panel.tree.isColumnHidden(SCREEN)
    assert panel.tree.topLevelItem(1).data(0, MATCH_ROLE) == 1


def test_the_element_shows_its_variants(store, panel):
    store.set_mode(Mode.TEST)

    store.set_test_result(found(TestScope.ELEMENT))

    assert not panel.tree.isColumnHidden(VARIANT)
    assert [row[1] for row in texts(panel)] == ["1 · LIGHT", "\u2003match", "\u2003match"]


def test_a_stale_result_stays_dimmed(store, panel):
    store.set_mode(Mode.EDIT)
    store.set_test_result(found())
    store.set_mode(Mode.TEST)
    assert not panel.stale.isVisible()

    store.set_field(ELEMENT, "timeout", 9)

    assert panel.stale.isVisible() and panel.tree.property("stale") is True
    assert len(texts(panel)) == 2


def test_an_error_shows_under_the_summary(store, panel):
    store.set_mode(Mode.TEST)

    store.set_test_result(TestResult(TestScope.VARIANT, 1, None, error="Screen 3 does not exist"))

    assert panel.error.full_text() == "Screen 3 does not exist" and not panel.tree.isVisible()
    assert panel.summary.height() == panel.summary.sizeHint().height()  # at the top, not stretched to the middle


def test_the_used_match_is_tinted_and_its_status_colored(store, theme, panel):
    store.set_mode(Mode.TEST)

    store.set_test_result(found())

    used, other = panel.tree.topLevelItem(0), panel.tree.topLevelItem(1)
    assert used.background(STATUS).color().name() == theme.palette.accent_tint.lower()
    assert used.foreground(STATUS).color().name() == theme.palette.accent.lower()
    assert used.font(STATUS).bold() and not other.font(STATUS).bold()
    assert other.background(STATUS).style() == Qt.BrushStyle.NoBrush


def test_resting_on_a_match_previews_it(store, panel, qtbot):
    store.set_mode(Mode.TEST)
    store.set_test_result(found())

    panel.tree.itemEntered.emit(panel.tree.topLevelItem(0), 0)
    assert not panel.preview.isVisible()  # not at once

    qtbot.waitUntil(panel.preview.isVisible, timeout=HOVER_DELAY_MS * 10)
    assert panel.preview.scale == 1


def test_a_match_chosen_with_the_keys_previews_it_at_once(store, panel, qtbot):
    store.set_mode(Mode.TEST)
    store.set_test_result(found())
    panel.tree.setFocus()
    qtbot.waitUntil(panel.tree.hasFocus)

    panel.tree.setCurrentItem(panel.tree.topLevelItem(1))

    assert panel.preview.isVisible()


def test_leaving_the_table_or_a_new_result_hides_the_preview(store, panel, qtbot):
    store.set_mode(Mode.TEST)
    store.set_test_result(found())
    panel.tree.setFocus()
    qtbot.waitUntil(panel.tree.hasFocus)
    panel.tree.setCurrentItem(panel.tree.topLevelItem(0))

    QApplication.sendEvent(panel.tree.viewport(), QEvent(QEvent.Type.Leave))
    assert not panel.preview.isVisible()

    panel.tree.setCurrentItem(panel.tree.topLevelItem(1))
    store.set_test_result(found())
    assert not panel.preview.isVisible()


def test_full_screen_shows_the_result_over_the_captures(store, panel, qtbot):
    store.set_mode(Mode.TEST)
    store.set_test_result(found())
    assert panel.full_screen.isVisible()

    panel.full_screen.click()

    session = panel.session
    assert session is not None and list(session.windows) == [1]
    for window in session.windows.values():
        qtbot.addWidget(window)
    with qtbot.waitSignal(session.finished):
        session.close()
    assert panel.session is None


def test_double_click_on_a_match_focuses_it_on_full_screen(store, panel, qtbot):
    store.set_mode(Mode.TEST)
    store.set_test_result(found())

    panel.tree.itemDoubleClicked.emit(panel.tree.topLevelItem(1), 0)

    window = panel.session.windows[1]
    qtbot.addWidget(window)
    assert window.focused == 1
    panel.session.close()


def test_no_full_screen_without_a_report(store, panel):
    store.set_mode(Mode.TEST)
    store.set_test_result(TestResult(TestScope.VARIANT, 1, None, error="Screen 3 does not exist"))

    assert not panel.full_screen.isVisible()
