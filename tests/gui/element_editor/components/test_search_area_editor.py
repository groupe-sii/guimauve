import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox

from guimauve.enums import ScreenArea
from guimauve.gui.element_editor_next.components import SearchAreaEditor, label_of
from guimauve.models.area import Area


@pytest.fixture
def editor(theme, qtbot):
    editor = SearchAreaEditor(theme)
    qtbot.addWidget(editor)
    editor.show()
    editor.emitted = []
    editor.edited.connect(editor.emitted.append)
    return editor


def combo(editor) -> QComboBox:
    return editor.findChild(QComboBox)


def labels(editor) -> list[str]:
    return [combo(editor).itemText(index) for index in range(combo(editor).count())]


def test_every_part_of_the_screen_is_offered_by_group(editor):
    shown = labels(editor)

    assert [label for label in shown if label] == [label_of(area) for area in ScreenArea]
    assert shown[:3] == ["Full screen", "", "Left half"]


def test_inherited_part_is_shown(editor):
    editor.set_value(ScreenArea.FULL, False, ScreenArea.FULL)

    assert combo(editor).currentText() == "Full screen"
    assert combo(editor).property("inherited") is True


def test_choosing_a_part_sets_it(editor):
    editor.set_value(ScreenArea.FULL, False, ScreenArea.FULL)
    index = labels(editor).index("Top half")

    combo(editor).setCurrentIndex(index)
    combo(editor).activated.emit(index)

    assert editor.emitted == [ScreenArea.TOP]


def test_custom_area_has_its_own_entry(editor):
    area = Area(left=120, top=80, right=760, bottom=440)
    editor.set_value(area, True, ScreenArea.FULL)

    index = combo(editor).currentIndex()
    assert combo(editor).currentText() == "Custom, 640 × 360"
    assert combo(editor).itemData(index, Qt.ItemDataRole.ToolTipRole) == "x 120, y 80, 640 × 360"


def test_custom_entry_leaves_with_the_custom_area(editor):
    editor.set_value(Area(left=0, top=0, right=10, bottom=10), True, ScreenArea.FULL)
    editor.set_value(ScreenArea.TOP, True, ScreenArea.FULL)

    assert not any(label.startswith("Custom") for label in labels(editor))


def test_draw_button_hidden_until_set(editor):
    assert not editor.draw.isVisible()


def test_draw_button(editor, qtbot):
    editor.set_draw(None)
    assert editor.draw.isVisible()

    with qtbot.waitSignal(editor.draw_requested):
        editor.draw.click()


def test_draw_button_unavailable(editor):
    editor.set_draw("No display")

    assert not editor.draw.isEnabled()
    assert editor.draw.toolTip() == "No display"
