import pytest
from PySide6.QtWidgets import QPushButton

from guimauve.gui.element_editor_next.canvas.test_bar import TestControls, TestSourceButton
from guimauve.gui.element_editor_next.components import CHECK
from guimauve.gui.element_editor_next.services import CaptureSource
from guimauve.gui.element_editor_next.state import TestScope


@pytest.fixture
def source(theme, qtbot):
    button = TestSourceButton(theme)
    qtbot.addWidget(button)
    return button


@pytest.fixture
def controls(theme, qtbot):
    widget = TestControls(theme)
    qtbot.addWidget(widget)
    widget.show()
    return widget


def items(button) -> dict[str, object]:
    return {action.text().split("\t")[0]: action for action in button.menu().actions() if action.text()}


def test_source_names_the_capture_and_offers_the_others(source, qtbot):
    source.set_source("Captured 14:02:31", 3, None)

    assert source.text() == "Captured 14:02:31"
    with qtbot.waitSignal(source.source_chosen) as chosen:
        items(source)["Instant"].trigger()
    assert chosen.args == [CaptureSource.INSTANT]


def test_initial_screen_disabled_without_initial_captures(source):
    source.set_source("Initial screen", 3, "No display")

    assert not items(source)["Initial screen"].isEnabled()


def test_delay_kept_is_ticked(source, qtbot):
    source.set_source("Initial screen", 5, None)
    delays = items(source)["After a delay"].menu()

    assert [action.text() for action in delays.actions()][:4] == ["1 s", "3 s", "5 s" + CHECK, "10 s"]
    with qtbot.waitSignal(source.delay_chosen) as chosen:
        delays.actions()[0].trigger()
    assert chosen.args == [1]


def test_code_switch_shows_only_with_code_overrides(controls, qtbot):
    controls.set_code(False, True)
    assert not controls.code.isVisible()

    controls.set_code(True, True)
    assert controls.code.isVisible() and controls.code.isChecked()
    with qtbot.waitSignal(controls.code_toggled) as toggled:
        controls.code.click()
    assert toggled.args == [False]


def test_scope(controls, qtbot):
    controls.set_scope(TestScope.ELEMENT)
    assert controls.scope.value() is TestScope.ELEMENT

    with qtbot.waitSignal(controls.scope_chosen) as chosen:
        next(b for b in controls.scope.findChildren(QPushButton) if b.text() == "Variant").click()
    assert chosen.args == [TestScope.VARIANT]


def test_run_tells_why_it_is_blocked(controls, qtbot):
    controls.set_run("Select a variant to test it")
    assert not controls.run.isEnabled() and controls.run.toolTip() == "Select a variant to test it"

    controls.set_run(None)
    assert controls.run.isEnabled() and "Run test" in controls.run.toolTip()
    with qtbot.waitSignal(controls.run_requested):
        controls.run.click()


def test_scope_keeps_its_height_in_a_taller_bar(controls):
    controls.resize(controls.width(), 3 * controls.scope.sizeHint().height())

    assert controls.scope.height() == controls.scope.sizeHint().height()
